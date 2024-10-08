import base64
import io
import numpy as np
import pandas as pd
from dash.exceptions import PreventUpdate
from flask_login import current_user
from app_factory.models import SensorImage, SensorInfo
from datetime import datetime
from sqlalchemy import update, text

import logging.config

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

            if content_type == "data:text/csv;base64" or content_type == "data:application/vnd.ms-excel;base64":
                df = pd.read_csv(io.StringIO(decoded.decode('ISO-8859-1')), sep=";", decimal=",")
                if all([elmt in df.columns for elmt in ['ANNEE', 'MOIS', 'JOUR', 'HEURE', 'MIN', 'SEC']]):
                    df["Date"] = pd.to_datetime(pd.DataFrame({
                        'year': df["ANNEE"],
                        'month': df["MOIS"],
                        'day': df["JOUR"],
                        'hour': df["HEURE"],
                        'minute': df['MIN'],
                        'second': df['SEC']}))
                    df.drop(["ANNEE", "MOIS", "JOUR", "HEURE", "MIN", "SEC"], axis=1, inplace=True)

                else:
                    raise ValueError("Les entêtes des colonnes de temps sont manquantes")

                if 'Capteur(mm)' in df.columns:
                    if 'Temp Int(°C)' not in df.columns: df['Temp Int(°C)'] = np.NAN
                    df.rename(columns={"Capteur(mm)": "mm", "Temp Int(°C)": "celsius"}, inplace=True)

                elif 'Ext1(mm)' in df.columns:
                    if 'Board Temp(°C)' not in df.columns: df['Board Temp(°C)'] = np.NAN
                    df.rename(columns={'Ext1(mm)': "mm", 'Board Temp(°C)': "celsius"}, inplace=True)
                else:
                    raise ValueError("Les entêtes des colonnes de deformations sont manquantes")

                df = df[['Date', 'mm', 'celsius']]


            else:
                provider = "Sites1D"
                sites_schema = {'Date': str, 'mm': float, '°C': float}
                df = pd.read_csv(io.StringIO(decoded.decode('ISO-8859-1')), sep="\t", skiprows=1, dtype=sites_schema)
                columns_selected = [col for col in df.columns if col in ['Date', 'mm', '°C']]
                df = df[columns_selected]
                if '°C' not in df.columns:
                    df['°C'] = np.NAN
                if set(df.columns) == set(sites_schema.keys()):
                    df = df.rename(columns={"°C": "celsius"})
                    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True)

                else:
                    df = pd.read_csv(io.StringIO(decoded.decode('utf-8')), sep='\t', skiprows=1, dtype=sites_schema)
                    columns_selected = [col for col in df.columns if col in ['Date', 'mm', 'celsius']]
                    df = df[columns_selected]
                    if set(df.columns) == set(sites_schema.keys()):
                        df["Date"] = pd.to_datetime(df["Date"], dayfirst=True)

                    else:
                        raise ValueError("Les entêtes des colonnes du fichier sont incorrectes")

        except Exception as e:
            mylogger.error(f"{current_user.email} importe un fichier avec l'erreur : {e}")
            return (
                [],  # store-data-uploaded'
                "",  # textarea-model
                "❌ As tu bien bien téléchargé les mesures d'un fissuromètre 1D SITES ou GINGER ?",  # ingest-message,
            )

        else:
            return (
                df.to_dict('records'),  # store-data-uploaded'
                f"{provider}",  # textarea-sensor-model
                f"Complètes la fiche du capteur 🖊️, puis lances l'intégration du fichier {filename}.",  # ingest-message
            )


def save_old_sensors_info(db, sensors_json, new_sensor_dict):
    sensors_df = pd.DataFrame(data=sensors_json)
    sensors_df.set_index('Id', inplace=True)
    sensor_id = new_sensor_dict["Id"]
    # calcul des différences
    old_sensor_dict = sensors_df.loc[sensor_id, :].to_dict()
    old_sensor_dict["Id"] = sensor_id

    diff_sensor = {k: new_sensor_dict[k] for k in new_sensor_dict if
                   new_sensor_dict.get(k) != old_sensor_dict.get(k)}

    # modification du sensor
    sensors_df.loc[sensor_id, :] = pd.Series(
        new_sensor_dict)  # attention :le format de la série passe dans la dataframe
    sensors_df.reset_index(inplace=True)
    sensors_json = sensors_df.to_dict("records")

    # formatage de la database
    new_sensor_dict['pk'] = None if new_sensor_dict['pk'] == '' else float(new_sensor_dict['pk'])
    new_sensor_dict['Ouverture_pose'] = None if new_sensor_dict['Ouverture_pose'] == '' else float(
        new_sensor_dict['Ouverture_pose'])
    new_sensor_dict['Date_pose'] = datetime.strptime(new_sensor_dict['Date_pose'], '%d/%m/%Y')
    new_sensor_dict['Date_depose'] = None if new_sensor_dict['Date_depose'] == '' else datetime.strptime(
        new_sensor_dict['Date_depose'], '%d/%m/%Y')
    new_sensor_dict['Date_collecte'] = None if new_sensor_dict['Date_collecte'] == '' else datetime.strptime(
        new_sensor_dict['Date_collecte'], '%d/%m/%Y')

    db.session.execute(update(SensorInfo), [new_sensor_dict])

    return sensors_json, diff_sensor


def save_new_sensors_info(db, sensors_json, new_sensor_dict):
    sensors_json.append(new_sensor_dict)

    sensor = SensorInfo(
        Id=new_sensor_dict["Id"],
        Reseau=new_sensor_dict["Reseau"][0] if type(new_sensor_dict["Reseau"]) == list else new_sensor_dict[
            "Reseau"],
        Ligne=new_sensor_dict["Ligne"][0] if type(new_sensor_dict["Ligne"]) == list else new_sensor_dict[
            "Ligne"],
        Modele=new_sensor_dict["Modele"],
        Latitude=float(new_sensor_dict["Latitude"]),
        Longitude=float(new_sensor_dict["Longitude"]),
        Ouverture_pose=None if new_sensor_dict["Ouverture_pose"] == '' else float(
            new_sensor_dict["Ouverture_pose"]),
        Date_pose=datetime.strptime(new_sensor_dict['Date_pose'], '%d/%m/%Y'),
        Date_depose=None if new_sensor_dict['Date_depose'] == '' else datetime.strptime(
            new_sensor_dict['Date_depose'], '%d/%m/%Y'),
        Num=new_sensor_dict["Num"],
        pk=None if new_sensor_dict["pk"] == '' else float(new_sensor_dict["pk"]),
        Divers=new_sensor_dict["Divers"],
        Zone=new_sensor_dict["Zone"],
        Lieu=new_sensor_dict["Lieu"],
        Date_collecte=None if new_sensor_dict['Date_depose'] == '' else datetime.strptime(
            new_sensor_dict['Date_collecte'], '%d/%m/%Y'))

    db.session.add(sensor)

    return sensors_json


def save_image(db, selected_data, image_content, image_name, card_id):
    try:
        if not (selected_data and 'points' in selected_data.keys() and selected_data['points'] != [] and image_content):
            raise ValueError("Il n'y a pas de point de selectionné ou d'image telechargé")

        sensor_id = selected_data['points'][0]['customdata'][0]
        content_format, content_string = image_content.split(',')
        if content_format not in ["data:image/jpg;base64", "data:image/png;base64"]:
            raise ValueError("Le fichier n'est pas une image (format png ou jpg).")
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


def query_sensors_info(db):
    sensors_dtype = {'Id': int, 'Num': str, 'Modele': str, 'Reseau': str, 'Ligne': str, 'Zone': str,
                     'Lieu': str, 'pk': str, 'Latitude': np.float64, 'Longitude': np.float64,
                     'Date_pose': 'datetime64[ns]', 'Date_depose': 'datetime64[ns]',
                     'Ouverture_pose': str, 'Date_collecte': 'datetime64[ns]'}

    sensors_df = pd.read_sql('select * from sensors_info_tb', con=db.engine, dtype=sensors_dtype)

    sensors_df.replace('None', '', inplace=True)
    sensors_df.replace('nan', '', inplace=True)

    sensors_df['Date_pose'] = sensors_df['Date_pose'].dt.strftime('%d/%m/%Y')
    sensors_df['Date_depose'] = sensors_df['Date_depose'].apply(lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else '')
    sensors_df['Date_collecte'] = sensors_df['Date_collecte'].apply(
        lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else '')

    return sensors_df.to_dict('records')


def save_measures(db, data, sensor_id):
    df = pd.DataFrame(data)  # to do faire la conversion en unix ici
    df["Date"] = pd.to_datetime(df["Date"])
    df["unix"] = df["Date"].apply(lambda x: int(x.timestamp()))
    df.drop('Date', inplace=True, axis=1)

    for index, row in df.iterrows():
        parameters = {'unix': row['unix'], 'mm': row['mm'], 'celsius': row['celsius']}
        query = ""
        if db.engine.name == 'sqlite':
            query = text(
                f"INSERT OR IGNORE INTO F{sensor_id} (unix, mm, celsius) VALUES (:unix, :mm, :celsius)")
        elif db.engine.name == 'mysql':
            query = text(
                f"INSERT IGNORE INTO F{sensor_id} (unix, mm, celsius) VALUES (:unix, :mm, :celsius)")
        db.session.execute(query, parameters)
