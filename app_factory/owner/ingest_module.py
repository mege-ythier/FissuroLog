import base64
import io
import sqlite3

import numpy as np
from dash import html
import pandas as pd
from dash.dash_table import DataTable
from dash.exceptions import PreventUpdate
from sqlalchemy.orm import session

from app_factory.models import SensorImage, Sensor
from datetime import datetime

from sqlalchemy import update

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
                    df.rename(columns={"Capteur(mm)": "mm", "Temp Int(°C)": "celsius"}, inplace=True)

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
                "Tu peux lancer l'intégration des mesures téléchargées à la database en appuyant sur le bouton correspond.",
            # ingest-message

            )




def save_sensors_info(db, sensors_json, new_sensor_dict):
    sensors_dtype = {'Id': str, 'Num': str, 'Modele': str, 'Reseau': str, 'Ligne': str, 'Zone': str, 'Lieu': str,
                     'pk': np.float64, 'Latitude': np.float64, 'Longitude': np.float64, 'Date_pose': str,
                     'Date_depose': str, 'Ouverture_pose': np.float64, 'Divers': str}

    sensors_df = pd.DataFrame(data=sensors_json, columns=sensors_dtype.keys())
    sensors_df = sensors_df.astype(sensors_dtype)

    # le sensor mis a jour
    sensor_id = new_sensor_dict["Id"]
    # cas 1 : ajout de mesures  à un capteur existant
    if 'Id' in sensors_df.columns and sensor_id in sensors_df['Id'].values:

        # dans le store
        sensors_df.set_index('Id', inplace=True)
        sensors_df.loc[sensor_id, :] = pd.Series(new_sensor_dict)  # new
        sensors_df.reset_index(inplace=True)
        sensors_json = sensors_df.to_dict("records")

        # dans la database
        new_sensor_dict['Date_pose'] = datetime.strptime(new_sensor_dict['Date_pose'], '%d/%m/%Y')
        new_sensor_dict['Date_depose'] = None if new_sensor_dict['Date_depose'] == "" else datetime.strptime(
            new_sensor_dict['Date_depose'], '%d/%m/%Y')

        db.session.execute(update(Sensor), [new_sensor_dict])
        db.session.commit()



    # cas2 : ajout de mesures  d'un nouveau capteur
    else:
        # BUG PREMIERE INJECTION
        sensors_json.append(new_sensor_dict)

        sensor = Sensor(
            Id=new_sensor_dict["Id"],
            Reseau=new_sensor_dict["Reseau"][0] if type(new_sensor_dict["Reseau"]) == list else new_sensor_dict[
                "Reseau"],
            Ligne=new_sensor_dict["Ligne"][0] if type(new_sensor_dict["Ligne"]) == list else new_sensor_dict[
                "Ligne"],
            Modele=new_sensor_dict["Modele"],
            Latitude=float(new_sensor_dict["Latitude"]),
            Longitude=float(new_sensor_dict["Longitude"]),
            Ouverture_pose=None if new_sensor_dict["Ouverture_pose"] == None else float(
                new_sensor_dict["Ouverture_pose"]),
            Date_pose=datetime.strptime(new_sensor_dict['Date_pose'], '%d/%m/%Y'),
            Date_depose=None if new_sensor_dict['Date_depose'] == '' else datetime.strptime(
                new_sensor_dict['Date_depose'], '%d/%m/%Y'),
            Num=new_sensor_dict["Num"],
            pk=None if new_sensor_dict["pk"] == None else float(new_sensor_dict["pk"]),
            Divers=new_sensor_dict["Divers"],
            Zone=new_sensor_dict["Zone"],
            Lieu=new_sensor_dict["Lieu"])
        db.session.add(sensor)
        db.session.commit()
    return sensors_json


def save_old_sensors_info(db, sensors_df, new_sensor_dict):
    # le sensor mis a jour
    sensor_id = new_sensor_dict["Id"]



    sensors_dtype = {'Id': str, 'Num': str, 'Modele': str, 'Reseau': str, 'Ligne': str, 'Zone': str,
                     'Lieu': str,
                     'pk': np.float64, 'Latitude': np.float64, 'Longitude': np.float64, 'Date_pose': str,
                     'Date_depose': str, 'Ouverture_pose': np.float64, 'Divers': str}

    sensors_df = sensors_df.astype(sensors_dtype)
    sensors_df.set_index('Id', inplace=True)


    sensors_df.loc[sensor_id, :] = pd.Series(new_sensor_dict,dtype=object)  # new #A VERIFIER pour la colonne id

    sensors_df.reset_index(inplace=True)
    sensors_json = sensors_df.to_dict("records")

    # dans la database
    new_sensor_dict['Date_pose'] = datetime.strptime(new_sensor_dict['Date_pose'], '%d/%m/%Y')
    new_sensor_dict['Date_depose'] = None if new_sensor_dict['Date_depose'] == "" else datetime.strptime(
        new_sensor_dict['Date_depose'], '%d/%m/%Y')

    db.session.execute(update(Sensor), [new_sensor_dict])
    db.session.commit()

    return sensors_json


def save_new_sensors_info(db, sensors_json, new_sensor_dict):
    sensors_json.append(new_sensor_dict)

    sensor = Sensor(
        Id=new_sensor_dict["Id"],
        Reseau=new_sensor_dict["Reseau"][0] if type(new_sensor_dict["Reseau"]) == list else new_sensor_dict[
            "Reseau"],
        Ligne=new_sensor_dict["Ligne"][0] if type(new_sensor_dict["Ligne"]) == list else new_sensor_dict[
            "Ligne"],
        Modele=new_sensor_dict["Modele"],
        Latitude=float(new_sensor_dict["Latitude"]),
        Longitude=float(new_sensor_dict["Longitude"]),
        Ouverture_pose=None if new_sensor_dict["Ouverture_pose"] == None else float(
            new_sensor_dict["Ouverture_pose"]),
        Date_pose=datetime.strptime(new_sensor_dict['Date_pose'], '%d/%m/%Y'),
        Date_depose=None if new_sensor_dict['Date_depose'] == '' else datetime.strptime(
            new_sensor_dict['Date_depose'], '%d/%m/%Y'),
        Num=new_sensor_dict["Num"],
        pk=None if new_sensor_dict["pk"] == None else float(new_sensor_dict["pk"]),
        Divers=new_sensor_dict["Divers"],
        Zone=new_sensor_dict["Zone"],
        Lieu=new_sensor_dict["Lieu"])
    db.session.add(sensor)
    db.session.commit()
    return sensors_json


def save_image_in_database(image_uploaded, image_name, db, sensor_id: str):
    if image_uploaded:

        try:
            # a ameliorer
            content_format, content_string = image_uploaded.split(',')
            if content_format != "data:image/png;base64":
                raise ValueError("Erreur : le fichier n'est pas une image au format png")
            decoded = base64.b64decode(content_string)

        except (AttributeError, ValueError) as e:
            image_uploaded_info = [f"# information sur l'intégration des images: {e}"]
        else:

            image = SensorImage(
                name=image_name,
                sensor_id=sensor_id,
                data=decoded
            )
            db.session.add(image)
            db.session.commit()
            image_uploaded_info = [f"# information sur l'intégration des images: succes {image_name}"]
    else:
        image_uploaded_info = ["# information sur l'intégration des images:  aucun fichier téléchargé par l'utilisateur"]

    return image_uploaded_info
