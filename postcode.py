# import relevant files
import streamlit as st
import pandas as pd
from streamlit_folium import folium_static
import folium
from folium.plugins import MarkerCluster
import requests
import json
import base64

# add sidebar logo and input
st.sidebar.image('logo.png')



postcodes = st.sidebar.file_uploader('File uploader', type=['xlsx'])
try:
    if postcodes is not None:
        file_details = {"FileName":postcodes.name,"FileType":postcodes.type,"FileSize":postcodes.size}
        st.write(file_details)
        df_pcode = pd.read_excel(postcodes, header=None)
        postcodes = df_pcode[0]
    else:
        st.write('Please upload an Excel file with all postcodes in the first column')
        postcodes = ['WC1B 3HF']
except:
    st.write('Error')
    
# get data

lat = []
lon = []
la = []
lsoa = []
ew = []
pc = []
region = []
county = []
progress_bar = st.progress(0)

with st.spinner('Running...'):
    for p in postcodes:
        try:
            r = requests.get('https://api.postcodes.io/postcodes/{}'.format(p))
            lat.append(r.json()['result']['latitude'])
            lon.append(r.json()['result']['longitude'])
            la.append(r.json()['result']['admin_district'].split(',')[0])
            lsoa.append(r.json()['result']['lsoa'])
            ew.append(r.json()['result']['admin_ward'])
            pc.append(r.json()['result']['parliamentary_constituency'])
            region.append(r.json()['result']['region'])
            county.append(r.json()['result']['admin_county'])
        except:
            print('Not a valid postcode')

    df = pd.DataFrame(list(zip(region, county, la, pc, ew, lsoa, lat, lon)), 
                    columns= ['Region', 'County','Local Authority', 'Parliamentary Constituency', 'Electoral Ward',
                            'LSOA', 'Latitude', 'Longitude'])

    df['IMD Decile'] =""
    df['IMD Rank'] =""
    df['IMD Score']=""

# append IMD

    for i in range(len(df)):
        s = requests.get('https://services3.arcgis.com/ivmBBrHfQfDnDf8Q/arcgis/rest/services/Indices_of_Multiple_Deprivation_(IMD)_2019/FeatureServer/0/query?where=lsoa11nm%3D%27{}%27&objectIds=&time=&geometry=&geometryType=esriGeometryEnvelope&inSR=&spatialRel=esriSpatialRelIntersects&resultType=none&distance=0.0&units=esriSRUnit_Meter&returnGeodetic=false&outFields=*&returnGeometry=true&returnCentroid=false&featureEncoding=esriDefault&multipatchOption=xyFootprint&maxAllowableOffset=&geometryPrecision=&outSR=&datumTransformation=&applyVCSProjection=false&returnIdsOnly=false&returnUniqueIdsOnly=false&returnCountOnly=false&returnExtentOnly=false&returnQueryGeometry=false&returnDistinctValues=false&cacheHint=false&orderByFields=&groupByFieldsForStatistics=&outStatistics=&having=&resultOffset=&resultRecordCount=&returnZ=false&returnM=false&returnExceededLimitFeatures=true&quantizationParameters=&sqlFormat=none&f=pjson&token='.format(df['LSOA'][i]))
        df['IMD Decile'].iloc[i] = s.json()['features'][0]['attributes']['IMDDec0']
        df['IMD Rank'].iloc[i] = s.json()['features'][0]['attributes']['IMDRank0']
        df['IMD Score'].iloc[i] = s.json()['features'][0]['attributes']['IMDScore']
st.success('Done!')


# create map
m = folium.Map(location=[df['Latitude'][0], df['Longitude'][0]],
               min_zoom=7, 
               max_zoom=16,
               zoom_start=15 )

folium.TileLayer(
        tiles = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr = 'Esri',
        name = 'Esri Satellite',
        overlay = False,
        control = True
       ).add_to(m)                 

style_0 = {'fillColor': '#2ca25f',  'color': '#2ca25f', "fillOpacity": 0.1, "weight": 1.7}

#geo_ap =  folium.GeoJson(data=(open("AP.json", "r", encoding="utf-8-sig")).read()).add_to(m)

ap = requests.get('https://raw.githubusercontent.com/jenniferbufton/flood_app/main/data/AP.json').json()

#ap_json = folium.GeoJson(data=('https://raw.githubusercontent.com/jenniferbufton/flood_app/main/AP.json'), style_function = lambda x:style_0).add_to(m)
fg = folium.FeatureGroup(name='Active Partnership', show=True)
m.add_child(fg)

for row in range(len(ap['features'])):
    ap_json = folium.GeoJson(data=(ap['features'][row]['geometry']), style_function = lambda x:style_0).add_to(fg)
    ap_json.add_child(folium.Popup(ap['features'][row]['properties']['Label']))

point = folium.FeatureGroup(name='Postcodes', show=True)
m.add_child(point)

marker_cluster = MarkerCluster().add_to(point)

for i in range(len(df)):
    folium.Circle(
      location=[df['Latitude'][i], df['Longitude'][i]],
      popup=('IMD Decile: {} \n IMD Rank: {:,}' .format(df['IMD Decile'].iloc[i],df['IMD Rank'].iloc[i])),
      radius=150,
      color='#dd3497',
      fill=True,
      fill_color='#dd3497',
        opacity=0.5,
        fill_opacity=0.7,
        ).add_to(marker_cluster)

folium.LayerControl(collapsed = False).add_to(m)

# add map
folium_static(m)

# add dataframe
st.write("#### Administrative Geographies and IMD:")
st.write(df)

def get_table_download_link_csv(df):
    #csv = df.to_csv(index=False)
    csv = df.to_csv().encode()
    #b64 = base64.b64encode(csv.encode()).decode() 
    b64 = base64.b64encode(csv).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="captura.csv" target="_blank">Download csv file</a>'
    return href

st.sidebar.markdown(get_table_download_link_csv(df), unsafe_allow_html=True)

