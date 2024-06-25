import pandas as pd
import base64
from app import ingest_final_step
from app import parse_file_and_update_ingest_card
from app import ingest_middle_step
from app import delete_table_final_step
from app import update_map


def test_ingest_middle_step():
    sensors_df = pd.read_csv("data_capteur/map.csv", sep=";")
    sensors = sensors_df.to_dict('records')

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
                                                                                                      metadata_stored=sensors)

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
    with open('test/2022-SITES-2565.txt', 'r') as f:
        file_content = f.read()
    # Encoder le contenu en base64
    encoded_content = base64.b64encode(file_content.encode()).decode()
    data, _, _, model, _ = parse_file_and_update_ingest_card('data:text/plain;base64,' + encoded_content, "test")
    assert model == "Sites1D"


def test_ingest_final_step():
    all_metadata_df = pd.read_csv("data_capteur/map.csv", sep=";")
    all_metadata = all_metadata_df.to_dict('records')

    metadata = dict(Table='test', Reseau="METRO", Ligne='14',
                    Modele='Sites1D', Num='2565',
                    Zone='raccord', Lieu='raccord',
                    Latitude='48.8390224', Longitude='2.3001811',
                    Date_depose='', Date_pose='24/02/2022', Ouverture_pose='-4')
    with open('test/2022-SITES-2565.txt', 'r') as f:
        file_content = f.read()
    # Encoder le contenu en base64
    encoded_content = base64.b64encode(file_content.encode()).decode()
    data, _, _, model, _ = parse_file_and_update_ingest_card('data:text/plain;base64,' + encoded_content, "test")

    all_metadata_with_new_sensors,_,_ = ingest_final_step(click=1, data=data, all_metadata=all_metadata,
                                                            metadata=metadata, image_contents=None)
    update_map(all_metadata_with_new_sensors)


def test_delete_table_final_step():
    delete_table_final_step(click=1, table_select="test", sensors_data={})
