# FissuroLog

# installation sur windows

python -m pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host=files.pythonhosted.org --upgrade pip
python -m pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host=files.pythonhosted.org virtualenv
python -m venv venv 
venv\Scripts\activate
python -m pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host=files.pythonhosted.org --upgrade pip
python -m pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host=files.pythonhosted.org -r requirement.txt
python app.py

# installation sur linux
Ouvres une console, places toi dans le dossier de l’application  
Crées ton environnement virtuel : python -m venv venv
Actives le :source venv/bin/activate  
Installes les libraries : pip install --no-index --find-links=python_librairies_linux -r requirement.txt  
Demarres ton application : python app.py



