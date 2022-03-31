# import relevant files
import streamlit as st
import pandas as pd
from streamlit_folium import folium_static
import folium
from folium.plugins import MarkerCluster
import requests
import json
import base64
import os
import click
import branca
from datetime import datetime

st.write('# Postcode Lookup')

# add sidebar logo and input
st.sidebar.image('logo.png')

st.sidebar.write('Enter a postcode in the "Postcode finder" widget')

try:
    latlon = st.sidebar.text_input('Postcode finder:', value='WC1B 3HF', max_chars=8, key=None, type='default')

    # get data

    lat = []
    lon = []
    la = []
    lsoa = []
    ew = []
    pc = []
    region = []
    county = []
    post = []

    # my_bar = st.progress(0)
    with st.spinner('Processing...'):
        def get_data(p_code):
            # my_bar.progress(i + 1)
            r = requests.get('https://api.postcodes.io/postcodes/{}'.format(p_code))
            lat.append(r.json()['result']['latitude'])
            lon.append(r.json()['result']['longitude'])
            la.append(r.json()['result']['admin_district'].split(',')[0])
            lsoa.append(r.json()['result']['lsoa'])
            ew.append(r.json()['result']['admin_ward'])
            pc.append(r.json()['result']['parliamentary_constituency'])
            region.append(r.json()['result']['region'])
            county.append(r.json()['result']['admin_county'])
            post.append(r.json()['result']['postcode'])

            df = pd.DataFrame(list(zip(post,region, county, la, pc, ew, lsoa, lat, lon)),
                            columns= ['Postcode','Region', 'County','Local Authority', 'Parliamentary Constituency', 'Electoral Ward',
                                    'LSOA', 'Latitude', 'Longitude'])
            return df

        df= get_data(latlon)

        df['IMD Decile'] =""
        df['IMD Rank'] =""
        df['IMD Score']=""

        # append IMD

        for i in range(len(df)):
            s = requests.get('https://services3.arcgis.com/ivmBBrHfQfDnDf8Q/arcgis/rest/services/Indices_of_Multiple_Deprivation_(IMD)_2019/FeatureServer/0/query?where=lsoa11nm%3D%27{}%27&objectIds=&time=&geometry=&geometryType=esriGeometryEnvelope&inSR=&spatialRel=esriSpatialRelIntersects&resultType=none&distance=0.0&units=esriSRUnit_Meter&returnGeodetic=false&outFields=*&returnGeometry=true&returnCentroid=false&featureEncoding=esriDefault&multipatchOption=xyFootprint&maxAllowableOffset=&geometryPrecision=&outSR=&datumTransformation=&applyVCSProjection=false&returnIdsOnly=false&returnUniqueIdsOnly=false&returnCountOnly=false&returnExtentOnly=false&returnQueryGeometry=false&returnDistinctValues=false&cacheHint=false&orderByFields=&groupByFieldsForStatistics=&outStatistics=&having=&resultOffset=&resultRecordCount=&returnZ=false&returnM=false&returnExceededLimitFeatures=true&quantizationParameters=&sqlFormat=none&f=pjson&token='.format(df['LSOA'][i]))
            df['IMD Decile'].iloc[i] = s.json()['features'][0]['attributes']['IMDDec0']
            df['IMD Rank'].iloc[i] = s.json()['features'][0]['attributes']['IMDRank0']
            df['IMD Score'].iloc[i] = s.json()['features'][0]['attributes']['IMDScore']

        # append AP
        ap_df = pd.read_csv('https://raw.githubusercontent.com/dominicwoodfine/Postcode-lookup/main/data/LA_ActivePartnerships_lookup_20200512.csv')
        ap_df = ap_df[['LA_Name', 'Active_Partnership_Label']]
        df = df.merge(ap_df, how='inner', left_on= 'Local Authority', right_on='LA_Name')
        df.drop(['LA_Name'], axis=1, inplace=True)
        df.rename({'Active_Partnership_Label': 'Active Partnership'}, axis=1, inplace=True)

        try:
            # API for OS
            #key = st.secrets["key"]
            date = datetime.now()
            key = '7mzGvy71yP6363qSVpAooF8AK8AEEPdX'
            layer = 'Outdoor_3857'
            zxy_path = 'https://api.os.uk/maps/raster/v1/zxy/{}/{{z}}/{{x}}/{{y}}.png?key={}'.format(layer, key)
    #print('=> Constructed OS Maps ZXY API path: {}'.format(zxy_path))
        # create map
            m = folium.Map(location=[df['Latitude'][0], df['Longitude'][0]],
                        min_zoom=7,
                        max_zoom=16,
                        zoom_start=15 )
        except:
            m = folium.Map(location=[51.108964, -0.754399],
                        min_zoom=7,
                        max_zoom=16,
                        zoom_start=15 )

        tile = folium.TileLayer(
                tiles = zxy_path,
                attr = 'Contains OS data © Crown copyright and database right {}'.format(date.year),
                name = 'OS Outdoor 3857',
                overlay = False,
                control = True
            ).add_to(m)

        folium.TileLayer(
                tiles = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attr = 'Esri',
                name = 'Esri Satellite',
                overlay = False,
                control = True
            ).add_to(m)

        style_0 = {'fillColor': '#2ca25f',  'color': '#2ca25f', "fillOpacity": 0.1, "weight": 1.7}

        ap = requests.get('https://raw.githubusercontent.com/dominicwoodfine/Postcode-lookup/main/data/AP.json').json()

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
            radius=50,
            color='#dd3497',
            fill=True,
            fill_color='#dd3497',
                opacity=0.5,
                fill_opacity=0.7,
                ).add_to(marker_cluster)

        folium.LayerControl(collapsed = False).add_to(m)

        st.success('Done!')

    # add map
    folium_static(m)

    # add dataframe
    st.write("#### Administrative Geographies and IMD Decile:")

    df.drop(['IMD Rank', 'IMD Score', 'Latitude', 'Longitude'], axis=1, inplace=True)

    st.table(df)

    def get_table_download_link_csv(df):
        csv = df.to_csv().encode()
        b64 = base64.b64encode(csv).decode()
        href = f'<a href="data:file/csv;base64,{b64}" download="Postcode.csv" target="_blank">Download CSV file:</a>'
        return href

    st.sidebar.write('### Download the results:')
    st.sidebar.markdown(get_table_download_link_csv(df), unsafe_allow_html=True)

except:
    st.sidebar.write('*Please use a valid postcode* :sunglasses:')
   # st.write('Use the file upload widget in the sidebar to upload a CSV file containing the postcodes you are looking up.')
   # st.write('The data should be structured as per the image below:')
  #  st.image('Example.JPG')

