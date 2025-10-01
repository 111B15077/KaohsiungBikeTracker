import requests
import pandas as pd
import plotly.express as px
import dash
from dash import dcc, html
from dash.dependencies import Input, Output

app_id = '111B15077-fb70a5bd-76ca-42de'
app_key = 'bfa58e7f-0195-4563-b279-4c00b2e6ce9f'

auth_url = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
station_url = "https://tdx.transportdata.tw/api/basic/v2/Bike/Station/City/Kaohsiung?%24top=30&%24format=JSON"
availability_url = "https://tdx.transportdata.tw/api/basic/v2/Bike/Availability/City/Kaohsiung?%24top=30&%24format=JSON"

class Auth:

    def __init__(self, app_id, app_key):
        self.app_id = app_id
        self.app_key = app_key

    def get_auth_header(self):
        headers = {
            'content-type': 'application/x-www-form-urlencoded'
        }
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.app_id,
            'client_secret': self.app_key
        }
        response = requests.post(auth_url, headers=headers, data=data)
        if response.status_code == 200:
            return response.json().get('access_token')
        else:
            print("Failed to authenticate.")
            return None

def fetch_data(url, token):
    headers = {
        'authorization': f'Bearer {token}'
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print("Failed to fetch data.")
        return None

def create_dataframe(station_data, availability_data):
    availability_dict = {item['StationUID']: item for item in availability_data}
    
    stations = []
    for station in station_data:
        station_uid = station['StationUID']
        availability = availability_dict.get(station_uid, {})
        station_info = {
            '站點名稱': station['StationName']['Zh_tw'],
            '可容納總數': station['BikesCapacity'],
            '可租借車數': availability.get('AvailableRentBikes', 0),
            '可歸還車數': availability.get('AvailableReturnBikes', 0),
            '地址': station['StationAddress']['Zh_tw'],
            '緯度': station['StationPosition']['PositionLat'],
            '經度': station['StationPosition']['PositionLon']
        }
        stations.append(station_info)
    
    return pd.DataFrame(stations)

def create_map_figure(df, selected_station=None):
    color = ['blue' if station == selected_station else 'fuchsia' for station in df['站點名稱']]
    fig = px.scatter_map(df, lat="緯度", lon="經度", hover_name="站點名稱",
                         hover_data={"可容納總數": True, "可租借車數": True, "可歸還車數": True, "地址": True},
                         size="可容納總數", size_max=15, color=color, color_discrete_sequence=["fuchsia", "blue"], zoom=12, height=600)
    fig.update_layout(mapbox_style="open-street-map")
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    return fig

if __name__ == "__main__":
    auth = Auth(app_id, app_key)
    token = auth.get_auth_header()
    if token:
        station_data = fetch_data(station_url, token)
        availability_data = fetch_data(availability_url, token)
        if station_data and availability_data:
            df = create_dataframe(station_data, availability_data)
            fig = create_map_figure(df)
            
            app = dash.Dash(__name__)
            app.layout = html.Div([
                dcc.Graph(id='map', figure=fig),
                html.Div(id='station-info', style={'padding': '20px'}),
                dcc.Dropdown(
                    id='station-dropdown',
                    options=[{'label': row['站點名稱'], 'value': row['站點名稱']} for index, row in df.iterrows()],
                    placeholder="選擇站點"
                )
            ])

            @app.callback(
                [Output('map', 'figure'), Output('station-info', 'children')],
                [Input('station-dropdown', 'value')]
            )
            def update_map(selected_station):
                if selected_station:
                    selected_data = df[df['站點名稱'] == selected_station].iloc[0]
                    fig = create_map_figure(df, selected_station)
                    fig.update_layout(mapbox_zoom=15, mapbox_center={"lat": selected_data['緯度'], "lon": selected_data['經度']})
                    station_info = html.Div([
                        html.P(f"站點名稱: {selected_data['站點名稱']}"),
                        html.P(f"可容納總數: {selected_data['可容納總數']}"),
                        html.P(f"可租借車數: {selected_data['可租借車數']}"),
                        html.P(f"可歸還車數: {selected_data['可歸還車數']}"),
                        html.P(f"地址: {selected_data['地址']}")
                    ])
                    return fig, station_info
                return create_map_figure(df), ""

            app.run(debug=True)