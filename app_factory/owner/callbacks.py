import base64
from datetime import datetime
import re

import numpy as np
from dash import html, Input, Output, State
from dash.exceptions import PreventUpdate
import pandas as pd

from flask_login import current_user, login_required
from sqlalchemy import update, text, desc

from app_factory.share.card_module import fig0
from app_factory.owner.ingest_module import parse_file_and_update_ingest_card, save_image_in_database, \
    save_new_sensors_info, save_old_sensors_info
from app_factory.share.fig_module import create_time_series_fig, create_map, query_time_series_data_and_create_fig

from app_factory.models import Sensor, SensorImage
from app_factory import db


def register_callbacks(dash_app):
    @dash_app.callback(
        Output('store-map-csv', 'data'),
        Output('welcome-info', 'children'),
        Input('url', 'pathname'), prevent_initial_call=True)
    def welcome(url):
        if current_user.is_authenticated:
            sensors_dtype = {'Id': str, 'Num': str, 'Modele': str, 'Reseau': str, 'Ligne': str, 'Zone': str,
                             'Lieu': str, 'pk': np.float64, 'Latitude': np.float64, 'Longitude': np.float64,
                             'Date_pose': str, 'Date_depose': str, 'Ouverture_pose': np.float64}

            sensors_df = pd.read_sql('select * from sensors_tb', con=db.engine, dtype=sensors_dtype,
                                     parse_dates={'Date_pose': '%Y-%m-%d %H:%M:%S.%f',
                                                  'Date_depose': '%Y-%m-%d %H:%M:%S.%f'})

            sensors_df["Date_pose"] = sensors_df['Date_pose'].dt.strftime('%d/%m/%Y')
            sensors_df["Date_depose"] = sensors_df['Date_depose'].dt.strftime('%d/%m/%Y')

            return sensors_df.to_dict('records'), f'Bienvenue {current_user.role} {current_user.email}'
        else:

            return [], "pas d'authentification"

    @dash_app.callback(
        Output('map', 'figure'),
        Input('store-map-csv', 'data'),
        State('map', 'selectedData'),
        prevent_initial_call=True, interval=10000)
    def update_map(sensors_json, selected_data):
        selected_point_index = -1

        if selected_data and 'points' in selected_data.keys() and selected_data['points'] != []:
            # premier point selectionné,id est la premiere valeur
            selected_sensor_id = selected_data['points'][0]['customdata'][0]
            sensors_df = pd.DataFrame(sensors_json)
            if sensors_df.shape[0] > 0:
                index = sensors_df.loc[sensors_df.Id == selected_sensor_id].index
                selected_point_index = -1 if len(index) == 0 else index[0]

        return create_map(sensors_json, selected_point_index)

    @dash_app.callback(
        Output('dropdown-line', 'options'),
        Input('dropdown-net', 'value'),
        prevent_initial_call=True, interval=10000)
    def update_line_options(net_value):
        line_options = []
        if "RER" in net_value:
            line_options += ["A", "B"]
        if "METRO" in net_value:
            line_options += ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14"]
        if "TRAM" in net_value:
            line_options += ["1", "2", "3,""4", "5", "6", "7", "8", "9", "10"]
        return line_options

    @dash_app.callback(Output('button_update_fig', 'hidden'),
                       Output('fig-message', 'children', allow_duplicate=True),
                       Input('date-picker-select', "start_date"),
                       Input('date-picker-select', "end_date"),
                       Input('aggregate-choice', 'value'),
                       State('dropdown-table', 'value'),
                       prevent_initial_call=True, interval=10000)
    def show_button(start_date, end_date, aggregate, table_value):
        if table_value:
            return False, "Appuies sur le bouton pour mettre à jour le graphique."
        else:
            raise PreventUpdate

    @dash_app.callback(
        Output('graph-time-series', 'figure', allow_duplicate=True),
        Output('button_update_fig', 'hidden', allow_duplicate=True),
        Output('fig-message', 'children', allow_duplicate=True),
        Output('image-card', 'children'),
        Output('textarea-model', "value"),
        Output('textarea-num', "value"),
        Output('textarea-zone', "value"),
        Output('textarea-lieu', "value"),
        Output('textarea-pk', "value"),
        Output('textarea-lat', "value"),
        Output('textarea-long', "value"),
        Output('textarea-date-pose', "value"),
        Output('textarea-date-depose', "value"),
        Output('textarea-delta', "value"),
        Output('textarea-divers', "value"),
        Output('dropdown-net', "value"),  # new
        Output('dropdown-line', "value"),  # new
        Output('dropdown-table', "value"),
        Input('button_update_fig', 'n_clicks'),
        Input('map', 'selectedData'),
        State('date-picker-select', "start_date"),
        State('date-picker-select', "end_date"),
        State('aggregate-choice', 'value'),
        State('store-map-csv', 'data'),
        Input('map', 'clickData'),

        prevent_initial_call=True, interval=10000)
    def update_with_click_on_map(n_click, selected_data, start_date, end_date, aggregate, data, click_data):

        fig = fig0
        fig_message = ("Aucun capteur n'est sélectionné. Click sur la carte pour sélectionner un capteur existant."
                       " Tu peux aussi ajouter un nouveau capteur.")


        image_card = html.H3("")

        model, num, zone, pk, place = "", "", "", "", ""
        lat, long = "", "",
        date_pose, date_depose = "", ""
        delta, divers = "", ""
        net, line = "", ""
        sensor_id = ""

        sensors_df = pd.DataFrame(data)

        # aucun point selectionné
        if selected_data is None or (
                selected_data and 'points' in selected_data.keys() and selected_data['points'] == []):

            if click_data and 'points' in click_data.keys() and type(
                    click_data['points'][0]['customdata']) == str:
                route = click_data['points'][0]['customdata']
                net = route.split(" ")[0]
                line = route.split(" ")[1]
                fig_message = "Click sur un point"


        else:
            # premier 0 car on prend seulement le premier point selectionné
            sensor_id = selected_data['points'][0]['customdata'][0]
            sensors_df = sensors_df.set_index("Id")

            model = sensors_df.loc[sensor_id, "Modele"]
            num = sensors_df.loc[sensor_id, "Num"]
            zone = sensors_df.loc[sensor_id, "Zone"]
            place = sensors_df.loc[sensor_id, "Lieu"]
            lat = sensors_df.loc[sensor_id, "Latitude"]
            long = sensors_df.loc[sensor_id, "Longitude"]
            pk = sensors_df.loc[sensor_id, "pk"]
            date_pose = sensors_df.loc[sensor_id, "Date_pose"]
            date_depose = sensors_df.loc[sensor_id, "Date_depose"]
            delta = sensors_df.loc[sensor_id, "Ouverture_pose"]
            divers = sensors_df.loc[sensor_id, "Divers"]
            net = sensors_df.loc[sensor_id, "Reseau"]
            line = sensors_df.loc[sensor_id, "Ligne"]

            if date_depose is None: date_depose = ""
            if pk is None: pk = ""
            if delta is None: delta = ""

            start_date_timestamp = datetime.strptime(start_date, "%Y-%m-%d").timestamp()
            end_date_timestamp = datetime.strptime(end_date, "%Y-%m-%d").timestamp()

            query = f"""
            SELECT strftime('%Y-%m-%d %H:%M:%S', datetime(unix,'unixepoch')) AS Date,mm,celsius
            FROM {sensor_id}
            WHERE  unix > {start_date_timestamp} and unix < {end_date_timestamp}
            """
            if aggregate == "oui":
                query = f"""
                    SELECT  strftime('%Y-%m-%d %H:00:00', datetime(unix,'unixepoch')) AS Date ,mm,celsius
                    FROM {sensor_id}
                    WHERE unix > {start_date_timestamp} and unix < {end_date_timestamp}
                    GROUP BY Date
                    ORDER BY Date
                """

            # measure_dtype = {'Unix': str, 'mm': np.float64, 'celsius': np.float64}
            df = pd.read_sql(query, con=db.engine)

            df = df.set_index('Date')
            df.index.name = "Date"
            size_on_memory = df.memory_usage(index=True, deep=False).sum()
            if size_on_memory > 200000:
                fig_message = "données trop volumineuses pour être affichées, modifier les options"

            if size_on_memory <= 200000:
                fig = create_time_series_fig(df, sensor_id, delta)
                fig_message = ("Un capteur est sélectionné. Ses mesures sont affichées sur le graphe."
                               " Tu peux modifier les informations de ce capteur, ou y ajouter de nouvelles mesures")

            try:
                # a voir : il y a plusieurs images
                query = f"""
                            SELECT data
                            FROM sensor_images
                            WHERE sensor_id ='{sensor_id}'
                            ORDER BY id DESC
                            LIMIT 1
                            """

                image_from_database = db.session.execute(text(query)).scalar()
                image_encoded = base64.b64encode(image_from_database).decode('utf-8')


            except TypeError:
                image_card = html.H3("il n'y a pas encore d'image du capteur dans les données du dashboard"),
            else:
                # a voir png, cherher le format
                image_card = html.Img(src=f"data:image/png;base64,{image_encoded}", width='100%'),

        return (fig, True, fig_message,
                image_card, model, num, zone, place, str(pk), str(lat), str(long), str(date_pose),
                str(date_depose), str(delta), divers, net, line, sensor_id)


def register_owner_callbacks(dash_app):
    @dash_app.callback(
        Output('button-update-metadata', 'hidden'),
        Output('button-delete-table', 'hidden'),
        Input('map', 'selectedData'),
        prevent_initial_call=True, interval=10000)
    def show_button(selected_data):
        if selected_data is None or (
                selected_data and 'points' in selected_data.keys() and selected_data['points'] == []):
            return True, True
        else:
            return False, False

    @dash_app.callback(
        Output('store-data-uploaded', 'data'),
        Output('upload-card-inner', 'children', allow_duplicate=True),
        Output('button-ingest', 'hidden'),
        Output('textarea-model', 'value', allow_duplicate=True),
        Output('ingest-message', 'children', allow_duplicate=True),
        Input('upload-file-dcc', 'contents'),
        State('upload-file-dcc', 'filename'), prevent_initial_call=True, interval=10000)
    def ingest_first_step(contents, filename):
        return parse_file_and_update_ingest_card(contents, filename)

    @dash_app.callback(
        Output('confirm-throw-ingestion', 'displayed'),
        Output('confirm-throw-ingestion', 'message'),
        Output('store-metadata-to-ingest', 'data'),
        Output('ingest-message', 'children', allow_duplicate=True),
        Output('upload-card-inner', 'children'),
        Input('button-ingest', 'n_clicks'),
        State('dropdown-table', 'value'),
        State('textarea-model', 'value'),
        State('textarea-num', 'value'),
        State('dropdown-net', 'value'),
        State('dropdown-line', 'value'),
        State('textarea-zone', 'value'),
        State('textarea-lieu', 'value'),
        State('textarea-pk', 'value'),
        State('textarea-long', 'value'),
        State('textarea-lat', 'value'),
        State('textarea-date-pose', 'value'),
        State('textarea-date-depose', 'value'),
        State('textarea-delta', 'value'),
        State('textarea-divers', 'value'),
        State('store-map-csv', 'data'),

        prevent_initial_call=True, interval=10000)
    def ingest_middle_step(click, sensor_select, model, num, net, line, zone, lieu, pk, long, lat, date_pose,
                           date_depose, delta, divers, sensors_json):
        ingest_card_message = f""
        confirm_message_is_displayed = False
        confirm_message = ""
        sensor_dict = None

        if click is None:
            raise PreventUpdate

        elif any(len(value) == 0 for value in [net, line]) and not sensor_select:
            ingest_card_message = "ECHEC : La ligne ou le réseau ne sont pas renseignés dans les menus déroulants"

        elif any(value == "" for value in [zone, model, lat, long]):
            ingest_card_message = "ECHEC : Des élements obligatoires ne sont pas renseignés dans le formulaire"

        # elif not (re.compile(r'^[a-zA-Z\s]+$').match(zone)):
        #     ingest_card_message = "Le nom de la zone est formé de lettres."

        elif not (re.compile(r'^-?\d*\.?\d*$').match(pk) or pk == ""):
            ingest_card_message = f"""Le pk est un chiffre."""

        elif not (re.compile(r'^-?\d*\.?\d*$').match(delta) or delta == ""):
            ingest_card_message = f"""L'ouverture est un chiffre."""

        elif not (re.compile(r'^-?\d*\.?\d*$').match(lat)):
            ingest_card_message = f"""La latitude est un chiffre."""

        elif not (re.compile(r'^-?\d*\.?\d*$').match(long)):
            ingest_card_message = f"""Le longitude est un chiffre."""

        elif not (re.compile(r'^[a-zA-Z0-9]+$').match(num) or num == ""):
            ingest_card_message = "ECHEC : Le numéro du capteur comporte uniquement des lettres ou des chiffres."

        elif not (re.compile(r'^\d{2}/\d{2}/\d{4}$').match(date_pose)):
            ingest_card_message = "ECHEC : Le date de pose est de la forme 01/01/2024."

        elif not (re.compile(r'^\d{2}/\d{2}/\d{4}$').match(date_depose) or date_depose == ""):
            ingest_card_message = "ECHEC : Le date de dépose est de la forme 01/01/2024."

        elif type(net) == list and len(net) > 1:
            ingest_card_message = "ECHEC : Sélectionne une seul reseau!"

        elif type(line) == list and len(line) > 1:
            ingest_card_message = "ECHEC : Sélectionne une seule ligne!"


        elif sensor_select:
            confirm_message_is_displayed = True
            confirm_message = f"""
            Les données de ton fichier vont étre intégrées au capteur existant {sensor_select}.  
            click ok, pour lancer l'intégration.
    
            click annuler, pour arrêter l'ingestion, puis choisis ou crée le bon capteur.      
    """

            sensor_dict = {'Id': sensor_select, 'Num': num, 'Modele': model,
                           'Reseau': net[0] if type(net) == list else net,
                           'Ligne': line[0] if type(line) == list else line,
                           'Zone': zone, 'Lieu': lieu,
                           'pk': np.float64('nan') if pk == '' else float(pk),
                           'Latitude': float(lat), 'Longitude': float(long), 'Date_pose': date_pose,
                           'Date_depose': date_depose,
                           'Ouverture_pose': np.float64('nan') if delta == '' else float(delta),
                           'Divers': divers}
        else:

            query = db.select(Sensor.Id).order_by(desc(Sensor.Id))
            sensor_last = db.session.execute(query).scalar()
            sensor_last_number = int(sensor_last.split("F")[1]) if sensor_last else 0
            sensor_created_number = sensor_last_number + 1
            sensor_created = "F" + str(sensor_created_number)

            confirm_message_is_displayed = True

            confirm_message = f"""
    Les données de ton fichier concernent un NOUVEAU capteur.
    Ce capteur s'appelera {sensor_created}.  
    Vérifies bien que ton capteur n'existe pas sous un autre nom.     
    Press OK pour lancer l'ingestion.
    """

            sensor_dict = {'Id': sensor_created, 'Num': num, 'Modele': model,
                           'Reseau': net[0] if type(net) == list else net,
                           'Ligne': line[0] if type(line) == list else line,
                           'Zone': zone, 'Lieu': lieu,
                           'pk': np.float64('nan') if pk == '' else float(pk),
                           'Latitude': float(lat), 'Longitude': float(long), 'Date_pose': date_pose,
                           'Date_depose': date_depose,
                           'Ouverture_pose': np.float64('nan') if delta == '' else float(delta),
                           'Divers': divers}

        return confirm_message_is_displayed, confirm_message, sensor_dict, ingest_card_message, ""

    @dash_app.callback(
        Output('text-error-upload-image', 'children'),
        Input('upload-image-dcc', 'contents'),
    )
    def show_message_upload_image(contents):
        try:
            content_format, content_string = contents.split(',')

            if content_format not in ["data:image/png;base64", "data:image/jpg;base64"]:
                return 'ECHEC : format != png ou jpg'
            decoded = base64.b64decode(content_string)
            if len(decoded) > 4000000:
                return 'ECHEC :taille > à 5Mo'

        except AttributeError:
            return "ECHEC : fichier != image"
        else:
            return "image OK"

    @dash_app.callback(

        Output('store-map-csv', 'data', allow_duplicate=True),
        Output('ingest-message', 'children', allow_duplicate=True),
        Output('image-message', 'children', allow_duplicate=True),
        Output('image-card', 'children', allow_duplicate=True),
        Output('dropdown-table', 'value', allow_duplicate=True),
        Output('graph-time-series', 'figure', allow_duplicate=True),
        Output('fig-message', 'children', allow_duplicate=True),
        Input('confirm-throw-ingestion', 'submit_n_clicks'),
        State('store-data-uploaded', 'data'),
        State('store-map-csv', 'data'),
        State('store-metadata-to-ingest', 'data'),
        State('upload-image-dcc', 'contents'),
        State('upload-image-dcc', 'filename'),
        State('date-picker-select', "start_date"),
        State('date-picker-select', "end_date"),
        State('aggregate-choice', 'value'),
        interval=10000, prevent_initial_call='initial_duplicate')
    def ingest_final_step(click, data, sensors_json, new_sensor_dict, image_contents,image_name, start_date, end_date, aggregate):

        if click is None or new_sensor_dict == {}:
            raise PreventUpdate

        else:
            sensor_id = new_sensor_dict["Id"]
            df = pd.DataFrame(data)

            def create_table(sensor_id):
                class Measure(db.Model):
                    __tablename__ = sensor_id
                    unix = db.Column(db.Integer, primary_key=True)
                    mm = db.Column(db.Float)
                    celsius = db.Column(db.Float)

                db.create_all()

            create_table(sensor_id)

            table_length_before = db.session.execute(text(f"SELECT COUNT(*) FROM {sensor_id};")).scalar()
            for index, row in df.iterrows():
                db.session.execute(
                    text(f"INSERT OR IGNORE INTO {sensor_id} (unix, mm, celsius) VALUES (:unix, :mm, :celsius)"),
                    {'unix': row['unix'], 'mm': row['mm'], 'celsius': row['celsius']}
                )

            db.session.commit()
            table_length_after = db.session.execute(text(f"SELECT COUNT(*) FROM {sensor_id};")).scalar()
            table_length = table_length_after - table_length_before
            database_info = (
                [f" # Information sur l'ingestion : le capteur {sensor_id} a {table_length} nouvelles mesures."])

            sensors_df = pd.DataFrame(data=sensors_json)


            if 'Id' in sensors_df.columns and sensor_id in sensors_df['Id'].values:
                sensors_json = save_old_sensors_info(db, sensors_df, new_sensor_dict)
            else:
                sensors_json = save_new_sensors_info(db, sensors_json, new_sensor_dict)

            image_upload_info = save_image_in_database(image_uploaded=image_contents, image_name = image_name, db=db, sensor_id=sensor_id)

            try:
                # a voir : il y a plusieurs images
                query = f"""
                            SELECT data
                            FROM sensor_images
                            WHERE sensor_id ='{sensor_id}'
                            ORDER BY id DESC
                            LIMIT 1
                            """

                image_from_database = db.session.execute(text(query)).scalar()
                image_encoded = base64.b64encode(image_from_database).decode('utf-8')

            except TypeError:
                image_card = html.H3("il n'y a pas encore d'image du capteur dans les données du dashboard"),
            else:
                # a voir png, cherher le format
                image_card = html.Img(src=f"data:image/png;base64,{image_encoded}", width='100%'),


            fig, fig_message = query_time_series_data_and_create_fig(db, sensor_id, start_date, end_date, aggregate,
                                                                     new_sensor_dict["Ouverture_pose"])

            return sensors_json, database_info, image_upload_info, image_card, sensor_id, fig, fig_message

    @dash_app.callback(

        Output('store-map-csv', 'data', allow_duplicate=True),
        Output('ingest-message', 'children', allow_duplicate=True),
        Output('image-message', 'children', allow_duplicate=True),
        Output('image-card', 'children', allow_duplicate=True),
        Input('button-update-metadata', 'n_clicks'),
        State('store-map-csv', 'data'),
        State('dropdown-table', 'value'),
        State('textarea-lat', 'value'),
        State('textarea-long', 'value'),
        State('textarea-pk', 'value'),
        State('textarea-delta', 'value'),
        State('textarea-num', 'value'),
        State('textarea-date-pose', 'value'),
        State('textarea-date-depose', 'value'),
        State('textarea-lieu', 'value'),
        State('textarea-zone', 'value'),
        State('textarea-divers', 'value'),
        State('textarea-model', 'value'),
        State('dropdown-net', 'value'),  # new
        State('dropdown-line', 'value'),  # new
        State('upload-image-dcc', 'contents'),
        State('upload-image-dcc', 'filename'),
        Prevent_initial_call=True, interval=10000, prevent_initial_call='initial_duplicate'

    )
    def update_sensors_info(click, sensors_json, sensor_id, lat, long, pk, delta, num, date_pose, date_depose,
                            lieu, zone, divers, model, net, line, image_contents,image_name):
        if click is None or sensor_id is None:
            raise PreventUpdate

        if pk == "": pk = np.float64('nan')
        if delta == "": delta = np.float64('nan')

        # validation des données du formulaire
        try:
            float(lat), float(long), float(pk), float(delta)

            if date_depose != "":
                datetime.strptime(date_depose, "%d/%m/%Y")

            if image_contents:
                content_format, content_string = image_contents.split(',')
                if content_format != "data:image/png;base64":
                    raise ValueError("fichier image invalide")

        except (TypeError, ValueError) as e:
            return sensors_json, f"echec de la mise à jour des données : {e}"

        except ValueError("fichier image invalide") as e:
            return sensors_json, f"echec de la mise à jour des données : {e}"

        else:
            sensor_updated = {'Id': sensor_id,
                              'Reseau': net[0] if type(net) == list else net,
                              'Ligne': line[0] if type(line) == list else line,
                              'Zone': zone, 'Lieu': lieu, 'pk': float(pk),
                              'Modele': model, 'Num': num, 'Latitude': float(lat), 'Longitude': float(long),
                              'Date_pose': date_pose,
                              'Date_depose': date_depose, 'Ouverture_pose': float(delta), 'Divers': divers}

            sensors_df = pd.DataFrame(sensors_json)
            sensors_json = save_old_sensors_info(db, sensors_df, sensor_updated)

            message_image = save_image_in_database(image_uploaded=image_contents,image_name=image_name, db=db, sensor_id=sensor_id)

            try:
                # a voir : il y a plusieurs images
                query = f"""
                            SELECT data
                            FROM sensor_images
                            WHERE sensor_id ='{sensor_id}'
                            ORDER BY id DESC
                            LIMIT 1
                            """

                image_from_database = db.session.execute(text(query)).scalar()
                image_encoded = base64.b64encode(image_from_database).decode('utf-8')


            except TypeError:
                image_card = html.H3("il n'y a pas encore d'image du capteur dans les données du dashboard"),
            else:
                # a voir png, cherher le format
                image_card = html.Img(src=f"data:image/png;base64,{image_encoded}", width='100%'),

            message = ["information du capteur mis a jour"]

            return sensors_json, message, message_image,image_card

    @dash_app.callback(
        Output('confirm-delete-table', 'displayed'),
        Output('confirm-delete-table', 'message'),
        Input('button-delete-table', 'n_clicks'),
        State('dropdown-table', 'value'),
        State('store-map-csv', 'data'),
        prevent_initial_call=True, interval=10000)
    def delete_table_first_step(click, sensor_select, sensors_json):
        if click is None or sensor_select is None:
            raise PreventUpdate
        else:
            confirm_message = f"Les données du capteurs {sensor_select} vont être supprimer."
            return True, confirm_message

    @dash_app.callback(
        Output('store-map-csv', 'data', allow_duplicate=True),
        Output('ingest-message', 'children', allow_duplicate=True),
        Output('dropdown-table', 'value', allow_duplicate=True),
        Output('graph-time-series', 'figure', allow_duplicate=True),
        Output('fig-message', 'children', allow_duplicate=True),
        Output('image-card', 'children', allow_duplicate=True),
        Input('confirm-delete-table', 'submit_n_clicks'),
        State('dropdown-table', 'value'),
        State('store-map-csv', 'data'),
        prevent_initial_call=True, interval=10000)
    def delete_table_final_step(click, sensor_select, sensors_json):
        if click is None:
            raise PreventUpdate
        elif sensor_select is None:
            raise PreventUpdate
        else:

            db.session.execute(text(f" DELETE FROM sensors_tb WHERE Id ='{sensor_select}'"))
            db.session.execute(text(f"DROP TABLE IF EXISTS {sensor_select}"))
            db.session.execute(text(f" DELETE FROM sensor_images WHERE sensor_id ='{sensor_select}'"))

            sensors_df = pd.DataFrame(sensors_json)
            sensors_df.set_index("Id", inplace=True)
            sensors_df.drop(sensor_select, inplace=True, axis=0)
            sensors_df.reset_index(inplace=True)
            db.session.commit()

            fig = fig0
            fig_message = ("Aucun capteur n'est sélectionné. Click sur la carte pour sélectionner un capteur existant."
                           " Tu peux aussi ajouter un nouveau capteur.")

            return sensors_df.to_dict('records'), f'capteur {sensor_select} supprimé', None, fig, fig_message, ""
