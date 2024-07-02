from typing import List
from flask import Flask
import base64
import json
import logging
import sqlite3
from datetime import datetime
import re
import os

import numpy as np
from dash import Dash, html, dcc, Input, Output, callback, State
from dash.exceptions import PreventUpdate
import pandas as pd



from flask_login import current_user, login_required, logout_user, login_manager, login_user
from sqlalchemy import select, update

from app_factory.card_module import fig0, generate_form_card, generate_button_card, generate_message_card
from app_factory.ingest_module import save_in_database
from app_factory.ingest_module import parse_file_and_update_ingest_card
from app_factory.fig_module import create_time_series_fig, create_map

from app_factory.models import Sensor
from app_factory import db


def register_callbacks(dash_app):
    @dash_app.callback(
        Output('welcome-info', 'children', allow_duplicate=True),
        Input('url', 'pathname'), prevent_initial_call=True)
    def display_welcome(url):
        if current_user.is_authenticated:
            return f'Bienvenue contributeur {current_user.email}'
        else:
            return "pas d'authentification"


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


    def encode_image(image_path):
        try:
            with open(image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        except FileNotFoundError:
            print("erreur")
        else:
            return f"data:image/png;base64,{encoded_string}"



#mise a jour de la ligne et du reseau quand on click sur le point ici
    @dash_app.callback(
        Output('graph-time-series', 'figure'),
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
        Output('dropdown-net', "value"),#new
        Output('dropdown-line', "value"),#new
        Output('button-update-metadata', 'hidden'),
        Output('button-delete-table', 'hidden'),
        Output('dropdown-table',"value"),
        #Input('button_update_fig', 'n_clicks'),
        Input('map', 'selectedData'),
        State('date-picker-select', "start_date"),
        State('date-picker-select', "end_date"),
        State('aggregate-choice', 'value'),
        State('store-map-csv', 'data'),#new
        Input('map', 'clickData'),#new

        prevent_initial_call=True, interval=10000)
    def update_next_click_on_map(selected_data, start_date, end_date, aggregate, data, click_data):
    #def update_with_table_changes(n_clicks, table_name, start_date, end_date, aggregate, data, click_data):
        #store = {}#new
        

        fig = fig0
        fig_message = ("Aucun capteur n'est sélectionné. Click sur la carte pour sélectionner un capteur existant."
                       " Tu peux aussi ajouter un nouveau capteur.")
        image_card = html.H3("")


        model, num, zone, pk, place =  "", "", "", "", ""
        lat, long = "", "",
        date_pose, date_depose = "", ""
        delta, divers = "", "" # new
        net, line = "", "" # new

        table_name=""

        button_update_metadata_is_hidden, button_delete_table_is_hidden = True, True

        sensors_df = pd.DataFrame(data)

        # si on a plusieurs points, aucun points electionne
        if selected_data is None or (
            selected_data and 'points' in selected_data.keys() and selected_data['points'] == []):


            if click_data and 'points' in click_data.keys() and type(click_data['points'][0]['customdata']) == str:#new
                route = click_data['points'][0]['customdata']
                net = route.split(" ")[0]
                line = route.split(" ")[1]


        else:
            # premier 0 car on prend le premier point selectionne
            table_name = selected_data['points'][0]['customdata'][0]

            sensors_df = sensors_df.set_index("Table")

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
            net = sensors_df.loc[table_name, "Reseau"]
            line = sensors_df.loc[table_name, "Ligne"]

             

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




        return (fig, True, fig_message,
                image_card, str(model), str(num), zone, place, str(pk), str(lat), str(long), str(date_pose),
                str(date_depose), str(delta), str(divers), str(net), str(line),
                button_update_metadata_is_hidden, button_delete_table_is_hidden, table_name)


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
    def ingest_middle_step(click, table_select, model, num, net, line, zone, lieu, pk, long, lat, date_pose,
                           date_depose, delta, divers, metadata_stored):
        ingest_card_message = f""
        confirm_message_is_displayed = False
        confirm_message = ""
        table_metadata = None
        
        
        metadata_stored_df = pd.DataFrame(metadata_stored)
        tables_stored=[]
        if 'Table' in metadata_stored_df.columns  :
            metadata_stored_df.set_index('Table', inplace=True)
            tables_stored= metadata_stored_df.index
        


        if click is None:
            raise PreventUpdate

        if any(len(value) == 0 for value in [net, line]) and not table_select:
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

        elif type(net) == list and len(net) > 1 : 
            ingest_card_message = "ECHEC : Sélectionne une seul reseau!"

        elif type(line) == list and len(line) > 1 : 
            ingest_card_message = "ECHEC : Sélectionne une seule ligne!"

    

        elif table_select:
            # on prendre la valeur du reseau et de la ligne dans le store

            net = metadata_stored_df.loc[table_select, "Reseau"]
            line = metadata_stored_df.loc[table_select, "Ligne"]
            table_metadata = table_select
            confirm_message_is_displayed = True
            confirm_message = f"""
            Les données de ton fichier vont étre intégrées au capteur existant {table_select}.  
            click ok, pour lancer l'intégration.
    
            click annuler, pour arrêter l'ingestion, puis choisis ou crée le bon capteur.      
    """

        else:

            line = line[0] if type(line)== list else line
            test=type(line)
            net = net[0] if type(net) == list else net
            net_dict = {"RER": "RER", "METRO": "M", "TRAM": "T"}
            table_created = net_dict[net] + str(int(datetime.today().replace(microsecond=0).timestamp()))
            table_metadata = table_created
            confirm_message_is_displayed = True
            # if table_created in tables:
            if table_created in tables_stored:
                confirm_message = f"""
    Il y a deja un capteur nommé {table_created} dans le dashboard.
    Les données de ton fichier vont être intégrées à ce capteur.  
    Press OK pour lancer l'ingestion.  
                """
            else:
                # todo: gere l'erreur la table se crée mais pas la ligne dans le csv
                confirm_message = f"""
    Les données de ton fichier concernent un nouveau capteur.
    Ce capteur s'appelera {table_created}.  
    Vérifies bien que ton capteur n'existe pas sous un autre nom.     
    Press OK pour lancer l'ingestion.
    """

        metadata = {'Reseau': net, 'Ligne': line, 'Zone': zone, 'Lieu': lieu, 'pk': pk, 'Modele': model,
                    'Num': num,
                    'Latitude': lat, 'Longitude': long, 'Date_pose': date_pose, 'Date_depose': date_depose,
                    'Ouverture_pose': delta, 'Table': table_metadata, 'Divers': divers}

        return confirm_message_is_displayed, confirm_message, metadata, ingest_card_message, ""


    @dash_app.callback(Output('text-error-upload-image', 'children'),
              Input('upload-image-dcc', 'contents'),
              )
    def show_message_upload_image(contents):
        try:
            content_format, content_string = contents.split(',')

            if content_format != "data:image/png;base64":
                return 'télécharge une image png'
            decoded = base64.b64decode(content_string)
            if len(decoded) > 4000000:
                return 'télécharge une image de taille inférieure à 5Mo'
            else:
                return "image prête pour l'ingestion"
        except AttributeError:
            return "aucune image téléchargée"


    @dash_app.callback(

        Output('store-map-csv', 'data'),
        Output('ingest-message', 'children', allow_duplicate=True),
        Output('dropdown-table', 'value', allow_duplicate=True),
        Input('confirm-throw-ingestion', 'submit_n_clicks'),
        State('store-data-uploaded', 'data'),
        State('store-map-csv', 'data'),
        State('store-metadata-to-ingest', 'data'),
        State('upload-image-dcc', 'contents'),
        interval=10000, prevent_initial_call='initial_duplicate')

    def ingest_final_step(click, data, all_metadata, metadata, image_contents):
        image_upload_info = ["aucune image uploadée"]
        # quand on lance l'appli le submit_n_clicks de confirm-throw-ingestion prend la valeur None et donc il y a un call
        sensors_dtype= {'Table':str, 'Num': str,'Modele': str,'Reseau': str, 'Ligne': str,'Zone': str, 'Lieu' : str,'pk': np.float64,  'Latitude': np.float64,  'Longitude': np.float64, 'Date_pose': str,'Date_depose' :str,'Ouverture_pose':np.float64 }

        if click is None:
            #raise PreventUpdate # le store n'est pas mis a jour a l'ouverture de l'appli
            #le store est mis a jour a l'ouverture de l'appli
            
   

            sensors_df = pd.read_sql('select * from sensors_tb',con=db.engine,dtype=sensors_dtype,
                              parse_dates={'Date_pose': '%Y-%m-%d %H:%M:%S.%f','Date_depose': '%Y-%m-%d %H:%M:%S.%f'})
 
            sensors_df["Date_pose"]=sensors_df['Date_pose'].dt.strftime('%d/%m/%Y')#new
            sensors_df["Date_depose"]=sensors_df['Date_depose'].dt.strftime('%d/%m/%Y')#new
            # sensors_df = pd.read_csv("data_capteur/map.csv", sep=";")
            return (sensors_df.to_dict('records'),(""), None)
                   
    
    
        elif metadata == {}:
            raise PreventUpdate
        else:
            table_name = metadata["Table"]
            df = pd.DataFrame(data)

            # sauvegarder les mesures dans une table de la database
            save_in_database(df, table_name)

            # extraire le nombre de ligne de la table ingérée
            conn = sqlite3.connect('data_capteur/database.db')
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            table_length = cursor.fetchone()[0]
            conn.close()

            # mise à jour du store

            all_metadata_df = pd.DataFrame(data = all_metadata, columns = sensors_dtype.keys())
            all_metadata_df = all_metadata_df.astype(sensors_dtype)
            # modification des metada d'une table existante
            if 'Table' in all_metadata_df.columns and table_name in all_metadata_df['Table'].values:
                
                all_metadata_df.set_index('Table', inplace=True)

                all_metadata_df.loc[table_name,:]=pd.Series(metadata)#new
                all_metadata_df.reset_index(inplace=True)
                all_metadata = all_metadata_df.to_dict("records")

                #on modifie une ligne dans la database
                metadata_to_sql = metadata
                metadata_to_sql["Reseau"]=metadata_to_sql["Reseau"][0] if type(metadata_to_sql["Reseau"])== list else metadata_to_sql["Reseau"]
                metadata_to_sql["Ligne"]=metadata_to_sql["Ligne"][0]if type(metadata_to_sql["Ligne"])== list else metadata_to_sql["Ligne"]
                metadata_to_sql["Latitude"] =float(metadata_to_sql["Latitude"])
                metadata_to_sql["Longitude"] =float(metadata_to_sql["Longitude"])
                metadata_to_sql["Ouverture_pose"]=None if metadata_to_sql["Ouverture_pose"]=="" else float(metadata_to_sql["Ouverture_pose"]) 
                metadata_to_sql['Date_pose']=datetime.strptime(metadata_to_sql['Date_pose'], '%d/%m/%Y')
                metadata_to_sql['Date_depose']= None if  metadata_to_sql['Date_depose'] == "" else datetime.strptime(metadata_to_sql['Date_depose'], '%d/%m/%Y')
                metadata_to_sql['pk']=None if metadata_to_sql["pk"]=="" else float(metadata_to_sql["pk"])
   
                
                db.session.execute(update(Sensor),[metadata_to_sql]) #new
                db.session.commit()
            # ajout des metadata d'une nouvelle table dans le store
            else:
                 # ajout du nouveau capteur dans la table des capteurs
                all_metadata.append(metadata)


       

                sensor=Sensor(
                    Table=metadata["Table"],
                    Reseau=metadata["Reseau"][0] if type(metadata["Reseau"])== list else metadata["Reseau"] ,
                    Ligne=metadata["Ligne"][0]if type(metadata["Ligne"])==list else metadata["Ligne"] ,
                    Modele=metadata["Modele"],
                    Latitude =float(metadata["Latitude"]),
                    Longitude =float(metadata["Longitude"]),
                    Ouverture_pose=None if metadata["Ouverture_pose"]=="" else float(metadata["Ouverture_pose"]), 
                    Date_pose=datetime.strptime(metadata['Date_pose'], '%d/%m/%Y'),
                    Date_depose= None if  metadata['Date_depose'] == "" else datetime.strptime(metadata['Date_depose'], '%d/%m/%Y'),
                    Num=metadata["Num"], 
                    pk=None if metadata["pk"]=="" else float(metadata["pk"]),
                    Divers=metadata["Divers"], 
                    Zone=metadata["Zone"],
                    Lieu=metadata["Lieu"])
                db.session.add(sensor)
                db.session.commit()
          

            database_info = ([
                f""" ### Information sur l'ingestion.
    Le capteur {table_name} a mesuré {table_length} ouvertures.
    """])

            try:
                content_format, content_string = image_contents.split(',')
                if content_format != "data:image/png;base64":
                    raise ValueError("Erreur : le fichier n'est pas une image au format png")
                decoded = base64.b64decode(content_string)
                images_path = f"data_capteur/images/{table_name}"
                if table_name not in os.listdir("data_capteur/images"): os.makedirs(images_path)

                images_name_file = os.listdir(images_path)
                images_number = [int(x.split(".")[0]) for x in images_name_file]
                image_number = 1
                if len(images_name_file) > 0:
                    image_number = max(images_number) + 1
            except (AttributeError, ValueError):
                image_upload_info = ["echec de l'intégration de l'image"]
            else:
                with open(f'{images_path}/{image_number}.png', 'wb') as f:
                    f.write(decoded)
                image_upload_info = ["succes de l'intégration de l'image"]

            return all_metadata, database_info + image_upload_info, table_name


    @dash_app.callback(

        Output('store-map-csv', 'data', allow_duplicate=True),
        Output('ingest-message', 'children', allow_duplicate=True),
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
        State('dropdown-net', 'value'),#new
        State('dropdown-line', 'value'),#new
        State('upload-image-dcc', 'contents'),
        Prevent_initial_call=True, interval=10000, prevent_initial_call='initial_duplicate'

    )
    def update_sensors_info(click, sensors_data_stored, table_name, lat, long, pk, delta, num, date_pose, date_depose, lieu,
                            zone, divers,net,line,
                            image_contents):
        if click is None or table_name is None:
            raise PreventUpdate

 
        if pk == "": pk = np.float64('nan')
        if delta == "": delta = np.float64('nan')
        try:
            float(lat), float(long), float(pk), float(delta)

            if date_depose != "":
                datetime.strptime(date_depose, "%d/%m/%Y")

            if image_contents:
                content_format, content_string = image_contents.split(',')
                if content_format != "data:image/png;base64":
                    raise ValueError("fichier image invalide")

        except (TypeError, ValueError) as e:
            return sensors_data_stored, f"echec de la mise à jour des données : {e}"

        except ValueError("fichier image invalide") as e:
            return sensors_data_stored, f"echec de la mise à jour des données : {e}"

        else:

            # new remplacer la valeur dans le store     
            sensor_updated = dict()
            sensor_updated["Latitude"] = float(lat)
            sensor_updated["Longitude"] = float(long)
            sensor_updated["Ouverture_pose"] = float(delta)
            sensor_updated["Num"] = num
            sensor_updated["pk"] = float(pk)
            sensor_updated["Divers"] = divers
            sensor_updated["Zone"] = zone
            sensor_updated["Lieu"] = lieu
            sensor_updated['Date_pose']=date_pose
            sensor_updated['Date_depose']=date_depose
            sensor_updated['Reseau']=net[0] if type(net) == list  else net#new
            sensor_updated['Ligne']=line[0] if type(line) == list else line#new
            
            sensors_df = pd.DataFrame(sensors_data_stored)
            sensors_df = sensors_df.set_index("Table")
            #remplacer la valeur dans le store
            # sensors_df.loc[table_name, "Latitude"] = float(lat)
            # sensors_df.loc[table_name, "Longitude"] = float(long)
            # sensors_df.loc[table_name, "Ouverture_pose"] = float(delta)
            # sensors_df.loc[table_name, "Date_pose"] = date_pose
            # sensors_df.loc[table_name, "Date_depose"] = date_depose
            # sensors_df.loc[table_name, "Num"] = num
            # sensors_df.loc[table_name, "pk"] = float(pk)
            # sensors_df.loc[table_name, "Divers"] = divers
            # sensors_df.loc[table_name, "Zone"] = zone
            # sensors_df.loc[table_name, "Lieu"] = lieu
            # sensors_df.reset_index(inplace=True)
            # sensors_data_stored = sensors_df.to_dict('records')
            sensors_df.loc[table_name, :] = pd.Series(sensor_updated)
            sensors_df.reset_index(inplace=True)
            sensors_data_stored = sensors_df.to_dict('records')
       

            #new remplacer la valeur dans la database
            sensor_updated["Table"] = table_name   
            sensor_updated['Date_pose']=datetime.strptime(date_pose, '%d/%m/%Y')
            sensor_updated['Date_depose']= None if date_depose == "" else datetime.strptime(date_depose, '%d/%m/%Y')
            db.session.execute(update(Sensor),[sensor_updated]) 
            db.session.commit()

    
            message = "information du capteur mis a jour"
            # ajouter une image
            if image_contents:
                content_format, content_string = image_contents.split(',')
                decoded = base64.b64decode(content_string)
                images_path = f"data_capteur/images/{table_name}"
                if table_name not in os.listdir("data_capteur/images"): os.makedirs(images_path)
                images_name_file = os.listdir(images_path)
                images_number = [int(x.split(".")[0]) for x in images_name_file]
                image_number = 1
                if len(images_name_file) > 0: image_number = max(images_number) + 1
                with open(f'{images_path}/{image_number}.png', 'wb') as f:
                    f.write(decoded)
                message = "information du capteur mis a jour et ingestion d'une nouvelle image"

            return sensors_data_stored, message


    @dash_app.callback(
        Output('confirm-delete-table', 'displayed'),
        Output('confirm-delete-table', 'message'),
        Input('button-delete-table', 'n_clicks'),
        State('dropdown-table', 'value'),
        State('store-map-csv', 'data'),
        prevent_initial_call=True, interval=10000)
    def delete_table_first_step(click, table_select, sensors_data):
        if click is None:
            raise PreventUpdate
        elif table_select is None:
            raise PreventUpdate
        else:
            confirm_message = f"""
        Les données du capteurs {table_select} vont être supprimer.         
    """
            return True, confirm_message


    @dash_app.callback(
        Output('store-map-csv', 'data', allow_duplicate=True),
        Output('ingest-message', 'children', allow_duplicate=True),
        Output('dropdown-table', 'value', allow_duplicate=True),
        Input('confirm-delete-table', 'submit_n_clicks'),
        State('dropdown-table', 'value'),
        State('store-map-csv', 'data'),
        prevent_initial_call=True, interval=10000)
    def delete_table_final_step(click, table_select, sensors_data):
        if click is None:
            raise PreventUpdate
        elif table_select is None:
            raise PreventUpdate
        else:
            sensors_df = pd.DataFrame(sensors_data)
            sensors_df.set_index("Table", inplace=True)
            sensors_df.drop(table_select, inplace=True, axis=0)
            sensors_df.reset_index(inplace=True)

            conn = sqlite3.connect('data_capteur/database.db')
            cursor = conn.cursor()
            cursor.execute(f"""DROP TABLE IF EXISTS {table_select} """)
            conn.commit()

            dossier_images_path = f"data_capteur/images/{table_select}"
            for file in os.listdir(dossier_images_path):
                images_path = os.path.join(dossier_images_path, file)
                if os.path.isfile(images_path):
                    # Supprimer le fichier
                    os.remove(images_path)

            os.rmdir(dossier_images_path)
            return sensors_df.to_dict('records'), f'capteur {table_select} supprimé', None


    @dash_app.callback(
            Output('map', 'figure'),
            # Output('dropdown-table', 'value'),
            # Output('map', 'selectedData'),
              Input('store-map-csv', 'data'),
              prevent_initial_call=True, interval=10000)
    def update_map(sensors_data):


        # to: callback lancer a l'ouverture de l'application: sauvegarde pour rien
        #ecrire les infos capteurs sur le serveur au format csv
        sensors_df = pd.DataFrame(sensors_data)
        sensors_df.to_csv("data_capteur/map.csv", index=False, sep=";", header=True, mode="w")
            
        return create_map(sensors_data)#,None



    

