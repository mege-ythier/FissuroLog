import base64
import io
import numpy as np
import pandas as pd
from dash.dash_table import DataTable
from dash.exceptions import PreventUpdate

from flask_login import current_user

from app_factory.models import SensorImage, SensorInfo
from datetime import datetime
from sqlalchemy import update, text

import logging.config

logging.config.fileConfig('logging.conf', disable_existing_loggers=True)
mylogger = logging.getLogger(__name__)


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


        except Exception as e:
            mylogger.warning(f"erreur dans le parsing {e}")
            return (
                {},  # store-data-uploaded'
                "",  # upload-card-inner
                True,  # button-ingest-hidden
                f"",  # textarea-model
                "❌ Erreur dans le parsing. Vérifies le fichier, Contactes amandine.mege-ythier@ratp.fr",
                # ingest-message,
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
                f"Complètes la fiche du capteur ,puis lances l'intégration du fichier {filename}.",  # ingest-message
                True

            )


def save_old_sensors_info(db, sensors_json, new_sensor_dict):

    # le sensor mis a jour
    try:

        # modification du store
        sensors_df = pd.DataFrame(data=sensors_json)

        for column in sensors_df.columns:
            sensors_df[column] = sensors_df[column].astype(str)

        sensors_df.replace('None', '', inplace=True)
        sensors_df.replace('nan', '', inplace=True)

        #attention les formats du dictionnaire est variables
        new_sensor_dict['Latitude'] = str(new_sensor_dict['Latitude'])
        new_sensor_dict['Longitude'] = str(new_sensor_dict['Longitude'])
        new_sensor_dict['Id'] = str(new_sensor_dict['Id'])
        for key, value in new_sensor_dict.items(): new_sensor_dict[key] ='' if new_sensor_dict[key] is None else new_sensor_dict[key]

        sensors_df.set_index('Id', inplace=True)
        sensor_id = new_sensor_dict["Id"]
        old_sensor_dict = sensors_df.loc[sensor_id, :].to_dict()
        old_sensor_dict["Id"] = sensor_id



        diff_sensor = {k: new_sensor_dict[k] for k in new_sensor_dict if
                       new_sensor_dict.get(k) != old_sensor_dict.get(k)}

        sensors_df.loc[sensor_id, :] = pd.Series(new_sensor_dict)  # le format de la serie passe dans la df
        sensors_df.reset_index(inplace=True)

        sensors_json = sensors_df.to_dict("records")

        # modification de la database

        new_sensor_dict['Latitude'] = float(new_sensor_dict['Latitude'])
        new_sensor_dict['Longitude'] = float(new_sensor_dict['Longitude'])

        new_sensor_dict['pk'] = None if new_sensor_dict['pk'] == '' else float(new_sensor_dict['pk'])

        new_sensor_dict['Ouverture_pose'] = None if new_sensor_dict['Ouverture_pose'] == '' else float(
            new_sensor_dict['Ouverture_pose'])

        new_sensor_dict['Date_pose'] = datetime.strptime(new_sensor_dict['Date_pose'], '%d/%m/%Y')
        new_sensor_dict['Date_depose'] = None if new_sensor_dict['Date_depose'] == '' else datetime.strptime(
            new_sensor_dict['Date_depose'], '%d/%m/%Y')
        new_sensor_dict['Date_collecte'] = None if new_sensor_dict['Date_collecte'] == '' else datetime.strptime(
            new_sensor_dict['Date_collecte'], '%d/%m/%Y')

        db.session.execute(update(SensorInfo), [new_sensor_dict])

    except Exception as e:
        mylogger.error(e)
        message = f"❌ ECHEC de la mise a jour des informations du capteur "
    else:

        mylogger.info(f"{current_user.email} met jour les informations {diff_sensor} du capteur  {sensor_id}")
        message = f"😍 Les informations  sont mis à jour "
        db.session.commit()

    return sensors_json, message


def save_new_sensors_info(db, sensors_json, new_sensor_dict):
    sensors_json.append(new_sensor_dict)

    try:

        sensor = SensorInfo(
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
            Lieu=new_sensor_dict["Lieu"],
            Date_collecte=None if new_sensor_dict['Date_depose'] == '' else datetime.strptime(
                new_sensor_dict['Date_collecte'], '%d/%m/%Y'))

        db.session.add(sensor)

    except Exception as e:
        mylogger.error(e)
    else:
        db.session.commit()

    return sensors_json


def save_image_in_database(db, selected_data, image_content, image_name, card_id):
    try:
        if not (selected_data and 'points' in selected_data.keys() and selected_data['points'] != [] and image_content):
            raise ValueError("Il n'y a pas de point de selectionné ou d'image telechargé")

        sensor_id = selected_data['points'][0]['customdata'][0]
        content_format, content_string = image_content.split(',')
        if content_format != "data:image/png;base64":
            raise ValueError("le fichier n'est pas une image au format png")
        decoded = base64.b64decode(content_string)
        if len(decoded) > 4000000:
            raise ValueError("L'image est trop grosse (> à 5Mo)'")

        query = text(f"""
             SELECT id
             FROM sensors_image_tb
             WHERE sensor_id= {sensor_id} AND card_id={card_id}
             """)
        image_id = db.session.execute(query).scalar()

        if image_id:
            image_dict = dict(
                id=image_id,
                name=image_name,
                sensor_id=sensor_id,
                data=decoded,
                card_id=card_id
            )
            db.session.execute(update(SensorImage), [image_dict])

        else:
            image = SensorImage(
                name=image_name,
                sensor_id=sensor_id,
                data=decoded,
                card_id=card_id
            )
            db.session.add(image)

    except Exception as e:
        image_uploaded_info = f" ❌ {e}"
        mylogger.error(f"{e}")

    else:
        db.session.commit()
        image_uploaded_info = f"Ajout de l'image {image_name} 👏 "
        mylogger.info(f"{current_user.email} ajoute l'image {image_name}")

    return image_uploaded_info
