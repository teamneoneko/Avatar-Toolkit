import json
import urllib.request
import csv
import typing
from os.path import dirname, isfile, join

current_translation_dict: dict = {}

def load_translation_dictionary(locale: str):
    translation_dict: dict = {}
    
    file: str = join(dirname(__file__), '..', 'assets', 'translations', locale+".json")


    #Web request from github the json from the "translations" branch in the translations folder. Message is what the HTTP response is from github, for if the file is not found. English should load normally by default.
    #TODO: We need this branch. Delete this todo if the "translations" branch exists and this code can retreive and save at least one json file.
    #TODO: Check if translations are out of date with some kind of version request, or just redownload perodically?
    #TODO: Handle the requested Locale code not having a translation dictionary on github therefore returning an error.
    try:
        if not isfile(file):
            file, Message = urllib.request.urlretrieve("https://raw.githubusercontent.com/unofficalcats/Avatar-Toolkit/translations/translations/"+locale+".json", file)

        with open(file, 'r') as f:
            translation_dict = json.load(f) #load the json with translations into memory 
    except:
        pass
    global current_translation_dict 
    current_translation_dict = translation_dict

def t(key: str) -> str: #Use this to translate keys to reduce clutter - @989onan
    if "messages" not in current_translation_dict: #just in case.
        print("loading translations")
        file: str = join(dirname(__file__), '..', 'assets', "settings.json")
        if isfile(file):
            with open(file, 'r') as f:
                settings = json.load(f) #load the json with translations into memory 
            print("loading selected language in assets/settings.json.")
            load_translation_dictionary(settings["ui_lang"])
        else:
            print("language not loaded from assets/settings.json because the file doesn't exist. loading us_en locale.")
            load_translation_dictionary("en_us")
    if key in current_translation_dict["messages"]:
        return current_translation_dict["messages"][key] #messages since json should also include contributing author names as well.
    return key

def get_supported_locales() -> list[str]:
    file: str = join(dirname(__file__), '..', 'assets', "supported_translations.csv")
    try:
        file, Message = urllib.request.urlretrieve("https://raw.githubusercontent.com/unofficalcats/Avatar-Toolkit/translations/supported_translations.csv", file)
        with open(file, 'r') as f:
            csv_file: list[str] = next(csv.reader(f))
            return csv_file
    except:
        return ["Error reading supported_translations.csv"]