
import base64
import io
import time
import numpy as np
import pandas as pd
from dash.dash_table import DataTable
from dash.exceptions import PreventUpdate

import logging.config

from flask_login import current_user
from sqlalchemy import text, Table, MetaData, Column, Float, Integer, inspect

from app_factory import db
from app_factory.utils.ingest import save_measures, query_sensors_info_and_create_sensors_json, save_old_sensors_info

logging.config.fileConfig('logging.conf', disable_existing_loggers=True)
mylogger = logging.getLogger(__name__)


def parse_file_and_update_ingest_card(contents, filename):

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

            if content_type == "data:text/csv;base64" or content_type == "data:application/vnd.ms-excel;base64":
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
                    df.rename(columns={"Capteur(mm)": "mm", "Temp Int(°C)": "celsius"}, inplace=True)

                    df["unix"] = df["Date"].apply(lambda x: int(x.timestamp()))
                else:
                    raise ValueError("Les entêtes des colonnes du fichier sont incorrectes")

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
                    df = df.rename(columns={"°C": "celsius"})
                    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True)
                    df["unix"] = df["Date"].apply(lambda x: int(x.timestamp()))

                else:
                    df = pd.read_csv(io.StringIO(decoded.decode('utf-8')), sep='\t', skiprows=1, dtype=sites_schema)
                    columns_selected = [col for col in df.columns if col in ['Date', 'mm', 'celsius']]
                    df = df[columns_selected]
                    if set(df.columns) == set(sites_schema.keys()):
                        df["Date"] = pd.to_datetime(df["Date"], dayfirst=True)
                        df["unix"] = df["Date"].apply(lambda x: int(x.timestamp()))

                    else:
                        raise ValueError("Les entêtes des colonnes du fichier sont incorrectes")

        except Exception as e:
            mylogger.warning(f"Erreur dans le parsing : {e}")
            return (
                {},  # store-data-uploaded'
                "",  # upload-card-inner
                True,  # button-ingest-hidden
                "",  # textarea-model
                "❌ As tu bien bien téléchargé un fichier de mesures brutes ?", # ingest-message,
                False
            )

        else:
            return (
                df.drop("Date", axis=1).to_dict('records'),  # store-data-uploaded'
                # upload-card-inner
                DataTable(
                    data=df.drop("unix", axis=1).to_dict('records'),
                    columns=[{'name': i, 'id': i} for i in df.drop("unix", axis=1).columns],
                    page_size=10
                ),
                False,  # button-card
                f"{provider}",  # textarea-sensor-model
                f"Complètes la fiche du capteur 🖊️, puis lances l'intégration du fichier {filename}.",  # ingest-message
                True

            )
