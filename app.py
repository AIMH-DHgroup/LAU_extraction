#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    wd_search.py

    Wikidata API
    `Search` module: Search for a library

    MIT License
"""

import requests
import os
import sys
import re
import csv
import json
import gzip
import time
import glob
from pathlib import Path
import argparse
import urllib.parse
import urllib.request
from shapely.geometry import shape
from shapely.ops import unary_union
from SPARQLWrapper import SPARQLWrapper, JSON

# import spacy

# Initialize the session
S = requests.Session()

# Wikidata query URL sparql
WD_URL = 'https://query.wikidata.org/sparql?query='
# Wikidata search api URL
URL = "https://www.wikidata.org/w/api.php"
# Value chain dataset
CSV_DATASET = 'vc_1.csv'
# LAU dataset
CSV_LAU = "eu_lau.csv"
# GeoJSON with LAU and NUTS
LAU = "geojson/LAU_RG_01M_2020_4326.geojson"
NUTS = "geojson/NUTS_RG_20M_2021_4326.geojson"



# Function to load a URL and return the content of the page
def loadURL(url, encoding='utf-8', asLines=False):
    request = urllib.request.Request(url)

    # Set headers
    request.add_header('User-Agent', 'Mozilla/5.0 (Windows)')
    request.add_header('Accept-Encoding', 'gzip')

    # Try to open the URL
    try:
        myopener = urllib.request.build_opener()
        f = myopener.open(request, timeout=120)
        url = f.geturl()
    except (urllib.error.URLError, urllib.error.HTTPError, ConnectionResetError):
        raise
    else:
        # Handle gzipped pages
        if f.info().get('Content-Encoding') == 'gzip':
            f = gzip.GzipFile(fileobj=f)
        # Return the content of the page
        return f.readlines() if asLines else f.read().decode(encoding)
    return None

# Function to perform a Wikidata query
# to retrieve the coords of a city
def wdQuery(qid):

    # Define SPARQL query 
    wdQuery = f'\nSELECT ?label ?coord ?coords\
                WHERE {{\
                wd:{qid} wdt:P31/wdt:P279* wd:Q56061.\
                wd:{qid} rdfs:label ?label.\
                OPTIONAL \
                {{ wd:{qid} wdt:P625 ?coord.}}\
                OPTIONAL \
                {{ wd:{qid} wdt:P159/wdt:P625 ?coords.}}\
                SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],it,la,en,fr,es,de". }}\
                }}'

    # Load query URL
    results = loadURL(f'{WD_URL}{urllib.parse.quote(wdQuery)}&format=json')

    # Return results
    if results:
        return json.loads(results)['results']['bindings']
    else:
        print(f'   Not found')
    return None

def osmQuery(qid):
    
    # Set up the SPARQL endpoint URL
    sparql = SPARQLWrapper("https://imagoarchive.it/fuseki/imago/query")
    # Set the SPARQL query string
    osm_query = f"""
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX geo: <http://www.opengis.net/ont/geosparql#>
    PREFIX osm: <https://www.openstreetmap.org/>
    PREFIX wd: <http://www.wikidata.org/entity/>
    SELECT ?geometry WHERE {{
    SERVICE <https://qlever.cs.uni-freiburg.de/api/osm-planet> {{
    ?geo geo:hasGeometry ?geometry .
    ?geo osm:wikidata wd:{qid} .
    ?geo rdf:type osm:relation .
    }}
    }}
    """
    
    # Set the query type to SELECT and the response format to JSON
    sparql.setQuery(osm_query)
    sparql.setReturnFormat(JSON)

    # Execute the SPARQL query and retrieve the results
    results = sparql.query().convert()

    # Print the results
    for result in results["results"]["bindings"]:
        return result["geometry"]["value"]
        

# Interactive Wikidata search
def wikiInteractive(name, wdEntities, qid, extra=''):
    extraString = f' • {extra}' if extra else '' # Questo non ci serve
    # print(f'   {name}{extraString.title()}\n')
    printed = False

    # For each entity that was found...
    # Per vedere come è fatta ogni entità che compone la risposta alla query
    # si può stampare wdEntities
    #print(wdEntities)
    label = ""
    label_it = ""
    label_en = ""
    coord = ""
    coords = ""
    country = ""
    gpe = ""
    # print(wdEntities)
    for entity in wdEntities:
        printed = True
        
        # Se trovo una entità che si chiama coord
        # prendo il suo valore
        # è possibile che ci siano più entità coord,
        # in tal caso prende l'ultimo valore
        # se si volesse prendere tutti i valori basta fare un
        # array o un dict
        if "coord" in entity:
            coord = entity["coord"]["value"]
        
        if "coords" in entity:
            coords = entity["coords"]["value"]

        # prendo ul valore se trovo un'entità di nomme label
        if "label" in entity:
            label = entity["label"]["value"] 
            lang = entity["label"]["xml:lang"]
            if lang == 'it':
                label_it = entity["label"]["value"]
            if lang == 'en':
                label_en = entity["label"]["value"]
            
            
        
        if "country" in entity:
            country = entity["country"]["value"] 

        if "gpe" in entity:
            gpe = entity["gpe"]["value"] 

        # se label non è vuoto
        # cerco una label in italiano o in inglese
        # la prima che trovo (a regola quella inglese)
        # restituisco l'iri, la label e le coord
        # lo posso fare perchè nella risposta (in wdEntities)
        # trovo sempre prima coord
        # if label != '':
        # # Get the entity label
        #     lang = entity["label"]["xml:lang"]
        #     if lang == 'it':
        #         if "label" in entity:
        #             label = entity["label"]["value"]
        #         if "country" in entity:
        #             country = entity["country"]["value"]
        #         if "gpe" in entity:
        #             gpe = entity["gpe"]["value"]
        #         print(f'   {qid} • {label} • {coord} • {country} • {gpe}\n')
        #         return f'http://www.wikidata.org/entity/{qid}', label, coord, country, gpe

        #     if lang == 'en':
        #         if "label" in entity:
        #             label = entity["label"]["value"]
        #         if "country" in entity:
        #             country = entity["country"]["value"]
        #         if "gpe" in entity:
        #             gpe = entity["gpe"]["value"]
        #         print(f'   {qid} • {label} • {coord} • {country} • {gpe}\n')
        #         return f'http://www.wikidata.org/entity/{qid}', label, coord, country, gpe

        

        # Print entity data
        # print(f'   {qid} • {label}\n')

        # Ask user to confirm
        # try:
        #     newQid = askUser(qid)
        # except KeyboardInterrupt:
        #     print('\n')
        #     sys.exit()

        # Return Wikidata IRI
        # if newQid:
        #     if newQid == qid:
        #         return wdIRI
        #     else:
        #         return f'http://www.wikidata.org/entity/{newQid}'
        #     break
    
    if label_it != "":
        # print(f'   {qid} • {label_it} • {coord} • {country} • {gpe}\n')
        return f'http://www.wikidata.org/entity/{qid}', label_it, coord, coords, country, gpe
    elif label_en != "":
        # print(f'   {qid} • {label_en} • {coord} • {country} • {gpe}\n')
        return f'http://www.wikidata.org/entity/{qid}', label_en, coord, coords, country, gpe
    else:
        # print(f'   {qid} • {label} • {coord} • {country} • {gpe}\n')
        return f'http://www.wikidata.org/entity/{qid}', label, coord, coords, country, gpe

# Function to search on Wikidata a place
def searchOnWikidata(place):

    # set the parameters of the API on Wikidata
    PARAMS = {
        "action": "query", 
        "format": "json",
        "list": "search",
        "srsearch": place # the search string
    }

    # Call the API
    R = S.get(url=URL, params=PARAMS)
    
    # Get the answer in JSON
    DATA = R.json()

    # Print the DATA variable to see how is made
    # print(DATA)
    
    # if there are results
    if DATA['query']['search']:
        # Call the WDQuery to get the coordinates
        for j in DATA['query']['search']:
            print(j['title'])
            geom = osmQuery(j['title'])
            
            if geom is not None:
                print(geom)
                return True, geom
            else:
                wdEntities = wdQuery(j['title'])
                if wdEntities:
                    wdIRI, label, coord, coords, country, gpe = wikiInteractive(place, wdEntities, j['title'])
                    if coord!="":
                        return True, coord
                    elif coords!="":
                        return True, coords
                    else:
                        return False, ""
                    break
                
    

# Function to convert coordinates in WKT
def convertWKT(exp):
    w = re.findall(r'\-?\d+\.\d+', exp)
    return "POINT ("+w[0]+" "+w[1]+")" 

# Function to uppercase the first letter
def first_uppercase(a):
    return a.group(1) + a.group(2).upper()

def ctr_code_from_vc_id(vc_id):
    w = re.findall(r'(?<=_)\w\w\w?\d?\s*?$', vc_id)
    if w[0][:2]=="GR":
        return ["EL"]
    elif w[0][:2]=="SE":
        return ["RS"]
    elif w[0]=="SCA":
        return ["NO","FI"]
    else:
        return [w[0][:2]]


# START the search -------------------------------
parser = argparse.ArgumentParser()
parser.add_argument('-n', '--nuts', action=argparse.BooleanOptionalAction, default=False)
# parser.add_argument('-b', '--bar-value', default=3.14)
args = parser.parse_args()
print (args.nuts)
    
print('=== LAU search ===\n')
       
# LOAD the GeoJSON files
with open(LAU) as f:
    gj = json.load(f)
with open(NUTS) as g:
    nuts = json.load(g)
    
# LOAD in a list the LAU dataset
# Header of the csv
# NUTS3 / LAU / NAME / NAME LATIN
lau_list=[]
with open(CSV_LAU, encoding='utf-8') as g:
    lau = csv.reader(g, delimiter=',')
    for i, row in enumerate(lau):
        lau = {} # create an empty dict
        
        # get the row values
        nuts3_code=row[0]
        lau_code=row[1]
        name=row[2]
        name_latin=row[3]
        
        # populate the dict
        lau['nuts3']=nuts3_code
        lau['lauCode']=lau_code
        lau['name']=name
        lau['nameLat']=name_latin
        
        # append the dict to the lau list
        lau_list.append(lau)
         

# nlp =  spacy.load('en_core_web_trf')

text = ""

# Create an empty dict for the story
story={}

# Counter to count found entities
count=0

# Counter to count N/A values
na=0

# Read the VC dataset
with open(CSV_DATASET, encoding='utf-8') as f:
    dataset = csv.reader(f, delimiter=',')

    # For each row of the TSV...
    for i, row in enumerate(dataset):
        
        text = text + row[2] + " " + row[3] + " "
        
        # Declare a list to store multiple lau
        multiple_lau=[]
        
        # the id of the value chain
        vc_id=row[1]
        # Name of the value chain
        name = row[2]
        # The mountain landcape value
        mountain_landscape = row[4]
        # The Value Chain lau code value
        vc_lau_code = row[5]
        
        ctr_code = ctr_code_from_vc_id(vc_id)
        
        # Declare found variable that will be set
        # True when a place will be found
        found=False
        
        # Declare multi variable, it will be set
        # True when a place is a composition of multiple 
        # LAU (e.g. multiple LAU codes)
        multi=False
        
        # if mountain landscape and vc lau code are N/A 
        # adding 1 to na counter and pass
        if(mountain_landscape=="N/A" and vc_lau_code=="N/A"):
            na=na+1
            pass

                
        # Some regex to clean mountain landscape value
        m_l=re.sub(r'\s(\(.*)', '', mountain_landscape) # Clen value in brackets
        m_l=re.sub(r'LAU\s?1\s', '', m_l) # Clean the words 'LAU' or 'LAU1'
        m_l=m_l.strip()
        
        # Some regex to clean VC_lau_code
        VC_l_c=re.sub(r'LAU\s?1\s?', '', vc_lau_code)  # Clean the words 'LAU' or 'LAU1'
        VC_l_c=re.sub(r'TR\d\d\d-', '', VC_l_c)  # Clean the prefix 'TR000'
        VC_l_c=re.sub(r'NUTS\s?3\s', '', VC_l_c) # Clean the words 'NUTS 3' or 'NUTS3'
           
        # print(VC_l_c)
        VC_l_c=re.sub(r'(?<=\d{5})\s.*$', '', VC_l_c) 
        # print(VC_l_c)
        
        if "LAU 1 not used" in vc_lau_code:
            try:
                start_index = vc_lau_code.index("„") + 1
                end_index = vc_lau_code.index("“", start_index)
                value = vc_lau_code[start_index:end_index]
                m_l = m_l + " " + value
                print(m_l)
            except:
                m_l = m_l
        
        # Uniformate multiple lau code in a list
        re_multiple="\d* and \d*"
        regex_multiple=re.compile(re_multiple)
        if re.match(regex_multiple, VC_l_c):
            find = re.findall(r'\d\d+', VC_l_c)
            f_lau=""
            for i in find:
                f_lau=f_lau+i+";"
            VC_l_c=f_lau
            
                
         
        # Corsica is an italian word, Translate the word in French
        if(m_l=="Corsica"):
            m_l="Corse"
            
        # Fix LAU code of some nation
        if 'IT' in ctr_code:
            if len(VC_l_c)==4:
                VC_l_c = '00'+VC_l_c
            if len(VC_l_c)==5:
                VC_l_c = '0'+VC_l_c
        elif 'PT' in ctr_code:
            VC_l_c = '0'+VC_l_c
        
        # if(row[0]=="PORTUGAL_ESTRELA"):
        #     l = "0"+l 
        
        # Uniformate Places in First capital letter format
        # if(m_l.isupper()):
        #     s1 = m_l.lower()
        #     s2 = re.sub("(^|\s)(\S)", first_uppercase, s1)
        #     m_l=s2
        
        m_l=m_l.lower()
            
            
        if "CH" in ctr_code:
            # print(m_l)
            if m_l!="n/a":
                # print(m_l)
        # if(row[0]=="SWITZERLAND_2"):
                # A list to store all the shapes
                m_shapes=[]
                n_lau=""
                ct_codes=""
                multi=False
                # Split all the lau codes
                multiple_lau=VC_l_c.split(";")
                # print(multiple_lau)
                for item in multiple_lau:
                    item = item.strip()
                    for feature in gj['features']:
                        if(feature['properties']['LAU_ID']==item):
                            # print(feature['properties']['LAU_ID'])
                            gg = shape(feature['geometry'])
                            m_shapes.append(gg)
                            n_lau = n_lau + feature['properties']['LAU_ID'] + ";"
                            # story[vc_id] = [gg.centroid, gg]
                            ct_codes=ct_codes+feature['properties']['CNTR_CODE'] +";"
                            multi=True
                if multi:
                    union = unary_union(m_shapes)
                    story[vc_id] = [ct_codes,n_lau,union.centroid, union]
                    found=True
            
        if len(VC_l_c.split(";")) > 1:
            # print(VC_l_c)
            m_shapes=[]
            n_lau=""
            ct_codes=""
            # Split all the lau codes
            multiple_lau=VC_l_c.split(";")
            # print(multiple_lau)
            for item in multiple_lau:
                item = item.strip()
                for feature in gj['features']:
                    if(feature['properties']['LAU_ID']==item):
                        # print(feature['properties']['LAU_ID'])
                        gg = shape(feature['geometry'])
                        m_shapes.append(gg)
                        n_lau = n_lau + feature['properties']['LAU_ID'] + ";"
                        # story[vc_id] = [gg.centroid, gg]
                        ct_codes=ct_codes+feature['properties']['CNTR_CODE'] +";"
            union = unary_union(m_shapes)
            story[vc_id] = [ct_codes,n_lau,union.centroid, union]
            found=True
            
        shapes = []
        n_lau = ""
        ct_codes = ""
        nuts_3= ""
        vc_lau_code_found = ""
        found_lau = False
        for lau_dict in lau_list:
            if not found:
                m_l = m_l.strip()
                if(m_l==lau_dict['name'].lower() or m_l==lau_dict['nameLat'].lower()):
                    # print("Found!" + row[17] + " - " + feature['properties']['LAU_NAME'])
                    # print(lau_dict['nuts3'][:2])
                    if lau_dict['nuts3'][:2] in ctr_code:
                        vc_lau_code_found = lau_dict['lauCode']
                        nuts_3=lau_dict['nuts3']
                        # story[vc_id] = [feature['properties']['CNTR_CODE'],feature['properties']['LAU_ID'],gg.centroid, gg]
                        found_lau=True
                        break
                # regex = re.compile(m_l, re.I)
                # if re.match(regex, lau_dict['name']):
                #     # print(lau_dict['nuts3'][:2])
                #     if lau_dict['nuts3'][:2] in ctr_code:
                #         # print("Found!" + row[17] + " - " + feature['properties']['LAU_NAME'])
                #         vc_lau_code_found = lau_dict['lauCode']
                #         # story[vc_id] = [feature['properties']['CNTR_CODE'],feature['properties']['LAU_ID'],gg.centroid, gg]
                #         nuts_3=lau_dict['nuts3']
                #         found_lau=True
                #         break
                # if re.match(regex, lau_dict['nameLat']):
                #     if lau_dict['nuts3'][:2] in ctr_code:
                #         # print("Found!" + row[17] + " - " + feature['properties']['LAU_NAME'])
                #         vc_lau_code_found = lau_dict['lauCode']
                #         # story[vc_id] = [feature['properties']['CNTR_CODE'],feature['properties']['LAU_ID'],gg.centroid, gg]
                #         nuts_3=lau_dict['nuts3']
                #         found_lau=True
                #         break
        for feature in gj['features']:
            if not found:
                if not found_lau:
                    m_l = m_l.rstrip()
                    if(m_l==feature['properties']['LAU_NAME'].lower()):
                        # print("Found!" + row[17] + " - " + feature['properties']['LAU_NAME'])
                        if feature['properties']['CNTR_CODE'] in ctr_code:
                            gg = shape(feature['geometry'])
                            story[vc_id] = [feature['properties']['CNTR_CODE'],feature['properties']['LAU_ID'],gg.centroid, gg]
                            found=True
                            break
            if not found:
                if not found_lau:
                    VC_l_c = VC_l_c.rstrip()
                    if(feature['properties']['LAU_ID']==VC_l_c):
                        # print(feature['properties']['LAU_ID'])
                        if feature['properties']['CNTR_CODE'] in ctr_code:
                            found=True
                            gg = shape(feature['geometry'])
                            story[vc_id] = [feature['properties']['CNTR_CODE'],feature['properties']['LAU_ID'],gg.centroid, gg]
                            break
                if found_lau:
                    # if feature['properties']['LAU_ID']==vc_lau_code:
                    #     # print(feature['properties']['LAU_ID'])
                    #     if ctr_code == feature['properties']['CNTR_CODE']:
                    #         print(ctr_code +" - " + feature['properties']['CNTR_CODE'])
                    #         found=True
                    #         gg = shape(feature['geometry'])
                    #         story[vc_id] = [feature['properties']['CNTR_CODE'],feature['properties']['LAU_ID'],gg.centroid, gg]
                    #         break
                    if feature['properties']['LAU_ID']==vc_lau_code_found:
                        if feature['properties']['CNTR_CODE'] in ctr_code:
                            found=True
                            gg = shape(feature['geometry'])
                            story[vc_id] = [feature['properties']['CNTR_CODE'],feature['properties']['LAU_ID'],gg.centroid, gg]
                            break
         
            
        if not found:
            # print(m_l)
            for feature in gj['features']:
                reg="^"+VC_l_c
                regex = re.compile(reg)
                if(re.match(regex, feature['properties']['LAU_ID'])):
                    if feature['properties']['CNTR_CODE'] in ctr_code:
                        gg = shape(feature['geometry'])
                        shapes.append(gg)
                        n_lau = n_lau + feature['properties']['LAU_ID'] + ";"
                        # story[vc_id] = [gg.centroid, gg]
                        found=True
                        multi = True
                        ct_codes=ct_codes+feature['properties']['CNTR_CODE'] +";"
                    
                # print(l)
                # for name in laus.keys():
                #     # print(name)
                #     if l == name:
                #         print(laus[l])
                #         count=count+1
            # l=re.findall(r'\d+', l)
            # for x in l:
            #     for feature in gj['features']:
            #         if(feature['properties']['LAU_ID']==x):
            #             found=True
            #             break
            if multi:
                un = unary_union(shapes)
                story[vc_id] = [ct_codes,n_lau, un.centroid, un]
        if not found:
            # print(m_l)
            m = re.findall(r'[aA][tT]\s\d{2}', m_l)
            if(m):
                n = re.sub(r'\s', '', m[0])
                n = n.upper()
                VC_l_c = n
            for n_feature in nuts['features']:
                if(n_feature['properties']['NUTS_ID']==VC_l_c):
                    gg = shape(n_feature['geometry'])
                    story[vc_id] = [n_feature['properties']['CNTR_CODE'],n_feature['properties']['NUTS_ID'], gg.centroid, gg]
                    found=True
                    break
                
                try:
                    if(m_l==n_feature['properties']['NAME_LATIN'].lower()):
                        gg = shape(n_feature['geometry'])
                        story[vc_id] = [n_feature['properties']['CNTR_CODE'],n_feature['properties']['NUTS_ID'], gg.centroid, gg]
                        found=True
                        break
                except:
                    if(m_l==n_feature['properties']['NUTS_NAME'].lower()):
                        gg = shape(n_feature['geometry'])
                        story[vc_id] = [n_feature['properties']['CNTR_CODE'],n_feature['properties']['NUTS_ID'], gg.centroid, gg]
                        found=True
                        break
        
        if not found:
            # print("-------------" + m_l)
            if(m_l!="n/a"):
                try:
                    b, coord = searchOnWikidata(m_l)
                    if(b):
                        story[vc_id] = ["","", convertWKT(coord), coord]
                        found=True
                except:
                    print(m_l)
        
        if not found:
            # print(nuts_3)  
            if nuts_3!="":
                for n_feature in nuts['features']:
                    if(n_feature['properties']['NUTS_ID']==nuts_3):
                        gg = shape(n_feature['geometry'])
                        story[vc_id] = [n_feature['properties']['CNTR_CODE'],n_feature['properties']['NUTS_ID'], gg.centroid, gg]
                        found=True
                        break
                    
        if(found):
            count=count+1
        else:
            if(m_l!="n/a"):
                print(m_l + " - " + VC_l_c)

# print(story)
print("Found: " + str(count))
print("Not found: " + str(455-count-na))
print("N/A: " + str(na))


with open(CSV_DATASET, 'r') as read_obj, open('output.csv', 'w', newline='') as write_obj:
    # Create a csv.reader object from the input file object
    csv_reader = csv.reader(read_obj)
    # Create a csv.writer object from the output file object
    csv_writer = csv.writer(write_obj)
    # Read each row of the input csv file as list
    row0 = ["Member State","Card ID","Descriptor of the value chain","Reference mountain chain","Reference mountain landscape","LAU","CTR Code", "Effective LAU o NUTS","Centroid","Shape"]
    csv_writer.writerow(row0)
    for row in csv_reader:
        # Pass the list / row in the transform function to add column text for this row
        try:            
            row.append(story[row[1]][0])
            row.append(story[row[1]][1])
            row.append(story[row[1]][2])
            row.append(story[row[1]][3])
        except:
            pass
        # transform_row(row, csv_reader.line_num)
        # Write the updated row / list to the output file
        csv_writer.writerow(row)
        

# doc = nlp(text)
# print("Noun phrases:", [chunk.text for chunk in doc.noun_chunks])
# print("Verbs:", [token.lemma_ for token in doc if token.pos_ == "VERB"])
# # Find named entities, phrases and concepts
# for entity in doc.ents:
#     print(entity.text, entity.label_)
# path = "Storymaps"
# files = Path(path).glob('*.csv') 
# # all_files = glob.glob(os.path.join(path , "/*.csv"))
# for filename in files:
#     with open(filename, encoding='utf-8') as f:
#         story = csv.reader(f, delimiter=',')
        
#         # For each row of the TSV...
#         r=0
#         entities={}
#         entity=""
#         name=""
#         for i, row in enumerate(story):
#             if(r==1):
#                 # print(row[0])
#                 for story in stories:
#                     if(row[0]==story['name']):
#                         name=row[0]
#                         # print("match")
#                         entity=entity+row[2]
#             elif(r>1):
#                 entity=entity+row[2]
              
#             r=r+1
#         entities[name]=entity
        
        # print(entities)           

    
# for feature in gj['features']:
#     print(feature)
#         # chiamo SEARCHPAGE il valore di ogni riga (row[0]) 
#         SEARCHPAGE = row[0]
#         # e imposto il valore name in library con il nome originale
#         # letto dal file. Library per adesso è un oggetto
#         # library = { 'name' : row[0] } dove row[0] è il nome
#         # della libreria
#         library['name'] = row[0]

#         # imposto i parametri per la chiamata alle api di ricerca
#         # su wikidata
#         PARAMS = {
#             "action": "query", 
#             "format": "json",
#             "list": "search",
#             "srsearch": SEARCHPAGE # il valore importante è questo, cioè la stringa di ricerca
#         }

#         # chiamo la query e prendo la riposta in data
#         R = S.get(url=URL, params=PARAMS)
#         DATA = R.json()

#         # se si vuol vedere come è fatto DATA basta stamparlo
#         # print(DATA)

#         # Cerco se c'è un risultato alla query di ricerca e prendo il primo, perché
#         # solitamente è quello più affidabile.
#         if DATA['query']['search']:
#             # faccio la query a wikidata chiamando la funzione wdQuery e passandogli il 
#             # valore dentro a title che è un qid
#             for j in DATA['query']['search']:
#                 wdEntities = wdQuery(j['title'])
#                 if wdEntities:
#                     wdIRI, label, coord, country, gpe = wikiInteractive(row[0], wdEntities, j['title'])
#                     break
#             # for i in len(DATA['query']['search']):
#             #     # fare un controllo per passare solamente i qid che sono istanza di glam
#             #     qidGlam = wdQuery(DATA['query']['search'][i]['title'])

#             #     # fare un controllo per passare solamente i qid che sono istanza di glam
#             #     wdEntities = wdQuery()
#                 # vado a estrarre i dati dalla risposta chiamando wikiInteractive
            


#             # Aggiorno l'oggetto library con i dati trovati
#             # adesso sarà un oggetto fatto così
#             # library = { 'name' : row[0],
#             #             'iri' : wdIri,
#             #             'label' : label,
#             #             'coord' : coord }
#             library['iri'] = wdIRI
#             library['label'] = label
#             library['coord'] = coord
#             library['country'] = country
#             library['gpe'] = gpe
#         else:
#             # altrimenti metto delle stringe vuote
#             library['iri'] = ""
#             library['label'] = ""
#             library['coord'] = ""
#             library['country'] = ""
#             library['gpe'] = ""

#         # scrivo nel file t 
#         t.write(library['name'])
#         t.write(" ----- ")
#         t.write(library['label'])
#         t.write(" ----- ")
#         t.write(library['iri'])
#         t.write(" ----- ")
#         t.write(library['coord'])
#         t.write(" ----- ")
#         t.write(library['country'])
#         t.write(" ----- ")
#         t.write(library['gpe'])
#         t.write("\n")

#         # Se voglio scrivere gli oggetti json basta attivare
#         # Dove LIBRARY_FILE è il nome del file da impostare nelle
#         # variabili globali iniziali e libraries il json con tutte
#         # le biblioteche
#         libraries[library['name']] = library
#         with open(LIBRARY_FILE, 'w', encoding='utf-8') as f:
#             json.dump(libraries, f, ensure_ascii=False)

# t.close()