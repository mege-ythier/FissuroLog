import base64
import io
import sqlite3

import numpy as np
from dash import html
import pandas as pd
from dash.dash_table import DataTable
from dash.exceptions import PreventUpdate


def parse_file_and_update_ingest_card(contents, filename):
    provider = ""
    df = pd.DataFrame({})
    if contents is None:
        raise PreventUpdate

    else:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)

        try:
            provider = "Ginger1D"
            ginger_schema = {
                'ANNEE': int,
                'MOIS': int,
                'JOUR': int,
                'HEURE': int,
                'MIN': int,
                'SEC': float,
                'Capteur(mm)': float,
                'Temp Int(°C)': float}

            if content_type == "data:text/csv;base64":
                df = pd.read_csv(io.StringIO(decoded.decode('ISO-8859-1')), dtype=ginger_schema, sep=";", decimal=",")
                columns_selected = [col for col in df.columns if col in ginger_schema.keys()]
                df = df[columns_selected]
                if 'Temp Int(°C)' not in df.columns:
                    df['Temp Int(°C)'] = np.NAN

                if set(df.columns) == set(ginger_schema.keys()):
                    df["Date"] = pd.to_datetime(pd.DataFrame({
                        'year': df["ANNEE"],
                        'month': df["MOIS"],
                        'day': df["JOUR"],
                        'hour': df["HEURE"],
                        'minute': df['MIN'],
                        'second': df['SEC']}))
                    df.drop(["ANNEE", "MOIS", "JOUR", "HEURE", "MIN", "SEC"], axis=1, inplace=True)
                    df.rename(columns={"Capteur(mm)": "mm", "Temp Int(°C)": "°C"}, inplace=True)

                    df["unix"] = df["Date"].apply(lambda x: int(x.timestamp()))
                else:
                    raise ValueError("Erreur : Le fichier csv ne correspond pas au schéma")

            else:
                provider = "Sites1D"
                sites_schema = {
                    'Date': str,
                    'mm': float,
                    '°C': float}
                df = pd.read_csv(io.StringIO(decoded.decode('ISO-8859-1')), sep="\t", skiprows=1, dtype=sites_schema)
                columns_selected = [col for col in df.columns if col in ['Date', 'mm', '°C']]
                df = df[columns_selected]
                if '°C' not in df.columns:
                    df['°C'] = np.NAN
                if set(df.columns) == set(sites_schema.keys()):
                    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True)
                    df["unix"] = df["Date"].apply(lambda x: int(x.timestamp()))

                else:
                    df = pd.read_csv(io.StringIO(decoded.decode('utf-8')), sep='\t', skiprows=1, dtype=sites_schema)
                    columns_selected = [col for col in df.columns if col in ['Date', 'mm', '°C']]
                    df = df[columns_selected]
                    if set(df.columns) == set(sites_schema.keys()):
                        df["Date"] = pd.to_datetime(df["Date"], dayfirst=True)
                        df["unix"] = df["Date"].apply(lambda x: int(x.timestamp()))

                    else:
                        raise ValueError("Erreur : Le fichier txt ne correspond pas au schéma")

                    # todo cas ou il y a pas les degres celcus ,3d(M5 raccordsaintmartin)

        except Exception as e:
            return (
                {},  # store-data-uploaded'
                # upload-card-inner
                html.Div(children=[
                    html.H3("Information sur le fichier téléchargé"),
                    html.H4(f"Le nom du fichier est {filename}."),
                    html.H4(f'{e} , Contactes amandine.mege-ythier@ratp.fr')
                ]),

                False,  # button-ingest
                f"",  # textarea-model
                "erreur dans le parsing",  # ingest-message
            )


        else:
            return (
                df.drop("Date", axis=1).to_dict('records'),  # store-data-uploaded'
                # upload-card-inner
                html.Div([
                    html.H4(f"fichier {filename} téléchargé"),
                    DataTable(
                        data=df.drop("unix", axis=1).to_dict('records'),
                        columns=[{'name': i, 'id': i} for i in df.drop("unix", axis=1).columns],
                        page_size=10
                    ),

                ]),
                False,  # button-card
                f"{provider}",  # textarea-sensor-model
                "Tu peux lancer l'intégration des mesures téléchargées à la database en appuyant sur le bouton correspond.",  # ingest-message

            )


def save_in_database(df, sensor_table):
    # Create sqlite database and cursor
    conn = sqlite3.connect('./data_capteur/database.db')
    cursor = conn.cursor()
    cursor.execute(f"""CREATE TABLE IF NOT EXISTS {sensor_table} (
                        mm real,
                        °C real,
                        unix INTEGER PRIMARY KEY
                        )""")
    conn.commit()

    for index, row in df.iterrows():
        conn.execute(f"INSERT OR IGNORE INTO {sensor_table} VALUES (?, ?, ?)",
                     (row['mm'], row['°C'], row['unix']))

    conn.commit()

    conn.close()

    return {}
