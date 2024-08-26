import numpy as np
import pandas as pd
import base64

from dash.exceptions import PreventUpdate
from sqlalchemy import text

from app_factory import db
from app_factory.utils.ingest import parse_file_and_update_ingest_card, save_old_sensors_info, save_new_sensors_info


from app_factory.callbacks import register_owner_callbacks

from app_factory import create_app





def test_ingest_first_step():
    with open('2022-SITES-2565.txt', 'r') as f:
        file_content = f.read()
    # Encoder le contenu en base64
    encoded_content = base64.b64encode(file_content.encode()).decode()
    data, _, _, model, _ = parse_file_and_update_ingest_card('data:text/plain;base64,' + encoded_content, "")
    assert model == "Sites1D"


def test_ingest_final_step():

    def ingest_final_step(click, data, sensors_json, new_sensor_dict, start_date, end_date, aggregate):

        if click is None or new_sensor_dict == {}:
            raise PreventUpdate

        else:
            sensor_id = new_sensor_dict["Id"]
            sensor_table = "F" + str(sensor_id)
            df = pd.DataFrame(data)

            def create_table(sensor_name):
                class Measure(db.Model):
                    __tablename__ = sensor_name
                    unix = db.Column(db.Integer, primary_key=True)
                    mm = db.Column(db.Float)
                    celsius = db.Column(db.Float)

                db.create_all()

            create_table(sensor_table)

            table_length_before = db.session.execute(text(f"SELECT COUNT(*) FROM {sensor_table};")).scalar()
            for index, row in df.iterrows():
                db.session.execute(
                    text(f"INSERT OR IGNORE INTO {sensor_table} (unix, mm, celsius) VALUES (:unix, :mm, :celsius)"),
                    {'unix': row['unix'], 'mm': row['mm'], 'celsius': row['celsius']}
                )

            db.session.commit()
            table_length_after = db.session.execute(text(f"SELECT COUNT(*) FROM {sensor_table};")).scalar()
            table_length = table_length_after - table_length_before
            database_info = (
                [f" # Information sur l'ingestion : le capteur {sensor_table} a {table_length} nouvelles mesures."])

            sensors_df = pd.DataFrame(data=sensors_json)

            if 'Id' in sensors_df.columns and sensor_id in sensors_df['Id'].values:
                sensors_json = save_old_sensors_info(db, sensors_json, new_sensor_dict)
            else:
                sensors_json = save_new_sensors_info(db, sensors_json, new_sensor_dict)

            fig, fig_message = query_time_series_data_and_create_fig_card(db, sensor_id, start_date, end_date, aggregate,
                                                                          new_sensor_dict["Ouverture_pose"])

            selected_data = {'points': [{'customdata': [sensor_id]}]}

            return sensors_json, database_info, str(sensor_id), fig, fig_message, selected_data, True

    app = create_app()
    register_owner_callbacks(app)

    sensors_dtype = {'Id': str, 'Num': str, 'Modele': str, 'Reseau': str, 'Ligne': str, 'Zone': str,
                     'Lieu': str, 'pk': np.float64, 'Latitude': np.float64, 'Longitude': np.float64,
                     'Date_pose': str, 'Date_depose': str, 'Ouverture_pose': np.float64}

    sensors_df = pd.read_sql('select * from sensors_tb', con=db.engine, dtype=sensors_dtype)
    sensors_df["Date_pose"] = sensors_df['Date_pose'].dt.strftime('%d/%m/%Y')
    sensors_df["Date_depose"] = sensors_df['Date_depose'].dt.strftime('%d/%m/%Y')
    sensors_json = sensors_df.to_dict('records')

    sensor_dict = dict(Id=100,
                       Reseau="METRO",
                       Ligne='14',
                       Modele='Sites1D',
                       Num='2565',
                       Zone='raccord',
                       Lieu='raccord',
                       Latitude='48.8390224',
                       Longitude='2.3001811',
                       Date_depose='',
                       Date_pose='24/02/2022',
                       Ouverture_pose='-4',
                       Divers='',
                       pk=None)




    with open('2022-SITES-2565.txt', 'r') as f:
        file_content = f.read()
    # Encoder le contenu en base64
    encoded_content = base64.b64encode(file_content.encode()).decode()
    data, _, _, model, _ = parse_file_and_update_ingest_card('data:text/plain;base64,' + encoded_content, "")

    sensors_json, database_info, sensor_id_str, fig, fig_message, selected_data, is_displayed= ingest_final_step(
        click=1,
        data=data,
        sensors_json=sensors_json,
        new_sensor_dict=sensor_dict,
        start_date="2020-01-01",
        end_date="2024-07-04",
        aggregate="non")

    assert sensor_id_str == '100'

    #create_map(sensors_json,-1)


