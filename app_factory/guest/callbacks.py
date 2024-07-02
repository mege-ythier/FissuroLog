
import base64
import sqlite3
from datetime import datetime
import os

from flask import session
import numpy as np
from dash import Dash, html, dcc, Input, Output, callback, State
from dash.exceptions import PreventUpdate
import pandas as pd

from flask_login import current_user, login_required, logout_user, login_manager, login_user

from app_factory.card_module import fig0

from app_factory.fig_module import create_time_series_fig, create_map
from app_factory import db
from app_factory.models import Sensor

def register_callbacks(dash_app):
    @dash_app.callback(
        Output('welcome-info', 'children'),
        Output('store-map-csv', 'data'),
        Input('url', 'pathname'), prevent_initial_call=True)
    def display_welcome(url):

        if current_user.is_authenticated:
            sensors_df = pd.read_sql('select * from sensors_tb',con=db.engine)#new
            sensors_df["Date_pose"] = pd.to_datetime(sensors_df["Date_pose"], format='%d/%m/%Y')#new
            sensors_df["Date_depose"] = pd.to_datetime(sensors_df["Date_depose"], format='%d/%m/%Y')#new



            return f'Bienvenue invité {current_user.email}',sensors_df.to_dict('records')
        else:
            return "pas d'authentification",[]
        

    @dash_app.callback(
            Output('map', 'figure'),
            Input('store-map-csv', 'data'),
            prevent_initial_call=True)
    def update_map(sensors_data):
         
        return create_map(sensors_data)#,None


    @dash_app.callback(
        Output('dropdown-line', 'options'),
        Input('dropdown-net', 'value'),
        State('map', 'selectedData'),
        prevent_initial_call=True, interval=10000)
    def update_line_in_control_card(net_value, selected_data):
        line_options = []
        if "RER" in net_value:
            line_options += ["A", "B"]
        if "METRO" in net_value:
            line_options += ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14"]
        if "TRAM" in net_value:
            line_options += ["1", "2", "3,""4", "5", "6", "7", "8", "9", "10"]
        #logger.info(f"selection du reseau {net_value}")
        if selected_data is None or (selected_data and 'points' in selected_data.keys() and selected_data['points'] == []):
            return line_options
        else:
            raise PreventUpdate


    @dash_app.callback(

        Output('dropdown-table', 'value', allow_duplicate=True),
        Input('dropdown-line', 'value'),
        Input('dropdown-net', 'value'),
        State('store-map-csv', 'data'),
        State('map', 'selectedData'),
        prevent_initial_call=True, interval=10000)
    def update_table_in_control_card(line_value, net_value, data_sensors, selected_data):
        df = pd.DataFrame(data_sensors)
        df["Ligne"] = df["Ligne"].astype(str)

        if selected_data is None or (selected_data and 'points' in selected_data.keys() and selected_data['points'] == []):
            return None

        elif 'points' in selected_data.keys() and selected_data['points'] != []:

            raise PreventUpdate

        else:
            raise PreventUpdate



    @dash_app.callback(Output('dropdown-net', 'value'),
              Output('dropdown-line', 'value'),
              Input('map', 'clickData'),
              prevent_initial_call=True, interval=10000
              )
    def update_control_card_with_click_on_line_map(click_data):
        route = click_data['points'][0]['customdata']
        net_click_value = None
        line_click_value = None
        # click sur la ligne
        if type(route) == str:
            net_click_value = route.split(" ")[0]
            line_click_value = route.split(" ")[1]
        if type(route) == list:
            raise PreventUpdate
        return [net_click_value], [line_click_value]


    @dash_app.callback(Output('dropdown-net', 'value', allow_duplicate=True),
              Output('dropdown-line', 'value', allow_duplicate=True),
              Output('dropdown-table', 'value', allow_duplicate=True),

              Input('map', 'clickData'),
              prevent_initial_call=True, interval=10000
              )
    def update_control_card_with_click_on_point_map(click_data):
        custom_data = click_data['points'][0]['customdata']
        table_click_value = None
        if type(custom_data) == list:
            net_click_value = [custom_data[1]]
            line_click_value = [custom_data[2]]
            table_click_value = custom_data[0]
            return net_click_value, line_click_value, table_click_value
        if type(custom_data) == str:
            raise PreventUpdate


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


    def encode_image(image_path):
        try:
            with open(image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        except FileNotFoundError:
            print("erreur")
        else:
            return f"data:image/png;base64,{encoded_string}"


    @dash_app.callback(
        #Output('store-time-serie', 'data'),
        Output('graph-time-series', 'figure'),#new
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
        # Output('button-update-metadata', 'hidden'),
        # Output('button-delete-table', 'hidden'),
        Input('button_update_fig', 'n_clicks'),
        Input('dropdown-table', 'value'),
        State('date-picker-select', "start_date"),
        State('date-picker-select', "end_date"),
        State('aggregate-choice', 'value'),
        State('store-map-csv', 'data'),
        State('textarea-model', "value"),

        prevent_initial_call=True, interval=10000)
    def update_with_table_changes(n_clicks, table_name, start_date, end_date, aggregate, data, model0):#new nom pas bon
        store = {}
        fig = fig0
        fig_message = ("Aucun capteur n'est sélectionné. Click sur la carte pour sélectionner un capteur existant."
                       " Tu peux aussi ajouter un nouveau capteur.")
        image_card = html.H3("")
        model, num, zone, pk, place, lat, long, date_pose, date_depose, delta, divers = model0, "", "", "", "", "", "", "", "", "", ""
        # button_update_metadata_is_hidden, button_delete_table_is_hidden = True, True

        sensors_df = pd.DataFrame(data)
        sensors_df = sensors_df.set_index("Table")

        if table_name:
            button_update_metadata_is_hidden = False
            button_delete_table_is_hidden = False
            model = sensors_df.loc[table_name, "Modele"]
            num = sensors_df.loc[table_name, "Num"]
            zone = sensors_df.loc[table_name, "Zone"]
            place = sensors_df.loc[table_name, "Lieu"]
            lat = sensors_df.loc[table_name, "Latitude"]
            long = sensors_df.loc[table_name, "Longitude"]
            pk = sensors_df.loc[table_name, "pk"]
            date_pose = sensors_df.loc[table_name, "Date_pose"]
            date_depose = sensors_df.loc[table_name, "Date_depose"]
            delta = sensors_df.loc[table_name, "Ouverture_pose"]
            divers = sensors_df.loc[table_name, "Divers"]

            if num is None: num = ""
            if date_depose is None: date_depose = ""
            if pk is None: pk = ""
            if delta is None: delta = ""
            if divers is None: divers = ""
            if type(pk) == np.float64 and np.isnan(pk) == True: pk = ""
            if type(delta) == np.float64 and np.isnan(delta) == True: delta = ""

            start_date_timestamp = datetime.strptime(start_date, "%Y-%m-%d").timestamp()
            end_date_timestamp = datetime.strptime(end_date, "%Y-%m-%d").timestamp()
            conn = sqlite3.connect('data_capteur/database.db')
            query = f"""
            SELECT strftime('%Y-%m-%d %H:%M:%S', datetime(unix,'unixepoch')) AS Date,mm,°C
            FROM {table_name}
            WHERE  unix > {start_date_timestamp} and unix < {end_date_timestamp}
            """
            if aggregate == "oui":
                query = f"""
                    SELECT  strftime('%Y-%m-%d %H:00:00', datetime(unix,'unixepoch')) AS Date ,mm,°C
                    FROM {table_name}
                    WHERE unix > {start_date_timestamp} and unix < {end_date_timestamp}
                    GROUP BY Date
                    ORDER BY Date
                """

            df = pd.read_sql_query(query, conn)
            df = df.set_index('Date')
            df.index.name = "Date"
            size_on_memory = df.memory_usage(index=True, deep=False).sum()
            if size_on_memory > 200000:
                fig_message = "données trop volumineuses pour être affichées, modifier les options"

            if size_on_memory <= 200000:
                store = df.to_dict('records')
                fig = create_time_series_fig(df, table_name, delta)
                fig_message = ("Un capteur est sélectionné. Ses mesures sont affichées sur le graphe."
                               " Tu peux modifier les informations de ce capteur, ou y ajouter de nouvelles mesures")

            try:
                images_path = f'data_capteur/images/{table_name}/'
                images_name_file = os.listdir(images_path)
                images_number = [int(x.split(".")[0]) for x in images_name_file]
                image_displayed = f'{images_path}{max(images_number)}.png'

            except FileNotFoundError:
                image_card = html.H3("il n'y a pas encore d'image du capteur dans les données du dashboard"),
            else:
                image_card = html.Img(src=encode_image(image_displayed), width='100%'),


        elif n_clicks is None:#new
            raise PreventUpdate



        return (#store,
            fig, True, fig_message,
                image_card, str(model), str(num), zone, place, str(pk), str(lat), str(long), str(date_pose),
                str(date_depose), str(delta), str(divers)
                )
                # ,button_update_metadata_is_hidden, button_delete_table_is_hidden)








