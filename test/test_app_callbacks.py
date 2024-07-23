import numpy as np
import pandas as pd
import base64

from app_factory import db
from app_factory.utils.ingest import parse_file_and_update_ingest_card
from app_factory.utils.fig import create_map


from app_factory.callbacks import register_owner_callbacks
# from app_factory.old_app import parse_file_and_update_ingest_card
# from app_factory.old_app import ingest_middle_step
# from app_factory.old_app import delete_table_final_step
# from app_factory.old_app import update_map

from app_factory import create_app

app = create_app()

def test_ingest_middle_step():
    sensors_dtype = {'Id': str, 'Num': str, 'Modele': str, 'Reseau': str, 'Ligne': str, 'Zone': str,
                     'Lieu': str, 'pk': np.float64, 'Latitude': np.float64, 'Longitude': np.float64,
                     'Date_pose': str, 'Date_depose': str, 'Ouverture_pose': np.float64}

    sensors_df = pd.read_sql('select * from sensors_tb', con=db.engine, dtype=sensors_dtype,
                             parse_dates={'Date_pose': '%Y-%m-%d %H:%M:%S.%f',
                                          'Date_depose': '%Y-%m-%d %H:%M:%S.%f'})

    sensors_df["Date_pose"] = sensors_df['Date_pose'].dt.strftime('%d/%m/%Y')
    sensors_df["Date_depose"] = sensors_df['Date_depose'].dt.strftime('%d/%m/%Y')

    sensors_json = sensors_df.to_dict('records')

    register_owner_callbacks(app)


    confirm_message_is_displayed, confirm_message, metadata, ingest_card_message = ingest_middle_step(click=1,
                                                                                                      table_select="M12_Sites1D_2565_20220224",
                                                                                                      tables=[
                                                                                                          "M12_Sites1D_2565_20220224"],
                                                                                                      model="Sites1D",
                                                                                                      num="2565",
                                                                                                      net=["METRO"],
                                                                                                      line=[12],
                                                                                                      zone="raccord",
                                                                                                      lieu="raccord",
                                                                                                      pk="0",
                                                                                                      long="2.3001811",
                                                                                                      lat="48.8390224",
                                                                                                      date_pose="24/02/2022",
                                                                                                      date_depose="",
                                                                                                      delta="-4",
                                                                                                      metadata_stored=sensors_json)

    table_select = "M12_Sites1D_2565_20220224"
    confirm_message_test = f"""
        Les données de ton fichier vont étre intégrées au capteur existant {table_select}.  
        click ok, pour lancer l'intégration.

        click annuler, pour arrêter l'ingestion, puis choisis ou crée le bon capteur.      
"""
    assert confirm_message_is_displayed == True
    assert ingest_card_message == ""
    assert confirm_message == confirm_message_test


def test_ingest_first_step():
    with open('2022-SITES-2565.txt', 'r') as f:
        file_content = f.read()
    # Encoder le contenu en base64
    encoded_content = base64.b64encode(file_content.encode()).decode()
    data, _, _, model, _ = parse_file_and_update_ingest_card('data:text/plain;base64,' + encoded_content, "")
    assert model == "Sites1D"


def test_ingest_final_step():
    sensors_dtype = {'Id': str, 'Num': str, 'Modele': str, 'Reseau': str, 'Ligne': str, 'Zone': str,
                     'Lieu': str, 'pk': np.float64, 'Latitude': np.float64, 'Longitude': np.float64,
                     'Date_pose': str, 'Date_depose': str, 'Ouverture_pose': np.float64}

    sensors_df = pd.read_sql('select * from sensors_tb', con=db.engine, dtype=sensors_dtype,
                             parse_dates={'Date_pose': '%Y-%m-%d %H:%M:%S.%f',
                                          'Date_depose': '%Y-%m-%d %H:%M:%S.%f'})

    sensors_df["Date_pose"] = sensors_df['Date_pose'].dt.strftime('%d/%m/%Y')
    sensors_df["Date_depose"] = sensors_df['Date_depose'].dt.strftime('%d/%m/%Y')

    sensors_json = sensors_df.to_dict('records')

    sensor_dict = dict(Table='test', Reseau="METRO", Ligne='14',
                       Modele='Sites1D', Num='2565',
                       Zone='raccord', Lieu='raccord',
                       Latitude='48.8390224', Longitude='2.3001811',
                       Date_depose='', Date_pose='24/02/2022', Ouverture_pose='-4')
    with open('2022-SITES-2565.txt', 'r') as f:
        file_content = f.read()
    # Encoder le contenu en base64
    encoded_content = base64.b64encode(file_content.encode()).decode()
    data, _, _, model, _ = parse_file_and_update_ingest_card('data:text/plain;base64,' + encoded_content, "")

    sensors_json_with_new_sensors, _, _ = ingest_final_step(click=1, data=data, all_metadata=sensors_json,
                                                            metadata=sensor_dict, image_contents=None)
    create_map(sensors_json_with_new_sensors,-1)


def test_delete_table_final_step():
    delete_table_final_step(click=1, table_select="test", sensors_data={})
