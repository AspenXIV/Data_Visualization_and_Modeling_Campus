"""Capital Bikeshare dashboard for Render."""
from pathlib import Path

import pandas as pd
import plotly.express as px
from dash import Dash, Input, Output, dcc, html


weather_labels = {1: 'Clear or partly cloudy', 2: 'Mist or cloudy', 3: 'Light rain or snow'}
weather_order = list(weather_labels.values())
weather_colors = dict(zip(weather_order, ['#126B70', '#4C68A5', '#AC5C24']))
rental_bins = list(range(0, 10001, 1000))


def prepare_bike_days(data):
    days = data.copy()
    days['date'] = pd.to_datetime(days['dteday'])
    days['year'] = days['date'].dt.year
    days['month'] = days['date'].dt.to_period('M').dt.to_timestamp()
    days['temperature_c'] = days['temp'] * 41
    days['weather'] = days['weathersit'].map(weather_labels)
    return days.sort_values('date')


def rental_histogram(days):
    counts = pd.cut(days['cnt'], bins=rental_bins, right=False).value_counts(sort=False)
    return pd.DataFrame({
        'Rental range': [f'{int(interval.left):,}-{int(interval.right) - 1:,}' for interval in counts.index],
        'Days': counts.to_numpy()
    })


def build_dashboard(data):
    days = prepare_bike_days(data)
    app = Dash(__name__)
    app.title = 'Capital Bikeshare and the weather'
    app.layout = html.Main([
        html.H1('Capital Bikeshare and the weather'),
        html.P('Compare daily demand by weather and temperature. Use the year filter to see whether the pattern shows up in both years. Built for bikeshare operations staff.'),
        html.Label('Year shown', htmlFor='year-filter'),
        dcc.Dropdown(
            id='year-filter',
            options=[
                {'label': 'Both years', 'value': 'all'},
                {'label': '2011', 'value': '2011'},
                {'label': '2012', 'value': '2012'}
            ],
            value='all', clearable=False,
            style={'maxWidth': '18rem', 'color': '#182332'}
        ),
        html.P(id='sample-size', role='status'),
        html.Div([
            dcc.Graph(id='rental-histogram'),
            dcc.Graph(id='weather-box'),
            dcc.Graph(id='temperature-scatter'),
            dcc.Graph(id='monthly-trend')
        ], style={'display': 'grid', 'gridTemplateColumns': 'repeat(auto-fit, minmax(min(100%, 460px), 1fr))', 'gap': '14px'}),
        html.H2('What the full dataset shows'),
        html.P('Rentals were usually lower on days with light rain or snow. They generally rose with temperature, and monthly averages were lower in winter.'),
        html.H2('Limits'),
        html.P('These are 2011-2012 totals from one system. Weather, season, and changes in ridership overlap, so this comparison cannot isolate the effect of weather.'),
        html.P([
            'Source: ',
            html.A('Bike Sharing, Hadi Fanaee-T and UCI', href='https://doi.org/10.24432/C5W894'),
            ' (CC BY 4.0).'
        ])
    ], style={'maxWidth': '1200px', 'margin': 'auto', 'padding': '20px', 'fontFamily': 'system-ui, sans-serif'})

    @app.callback(
        Output('sample-size', 'children'),
        Output('rental-histogram', 'figure'),
        Output('weather-box', 'figure'),
        Output('temperature-scatter', 'figure'),
        Output('monthly-trend', 'figure'),
        Input('year-filter', 'value')
    )
    def update_figures(year):
        selection = days if year == 'all' else days[days['year'].astype(str) == year]
        weather_counts = selection['weather'].value_counts().reindex(weather_order, fill_value=0)
        sample = f'{len(selection):,} days shown. ' + ' | '.join(
            f'{label}: {count:,}' for label, count in weather_counts.items()
        )
        weather_options = {
            'color': 'weather',
            'color_discrete_map': weather_colors,
            'category_orders': {'weather': weather_order},
            'labels': {'weather': 'Daily weather', 'cnt': 'Rentals per day', 'temperature_c': 'Temperature (°C)', 'date': 'Date'}
        }
        histogram = px.bar(
            rental_histogram(selection), x='Rental range', y='Days', title='Daily rental totals',
            labels={'Rental range': 'Rentals per day (1,000-rental bins)'}
        )
        histogram.update_traces(marker_color='#126B70')
        box = px.box(selection, x='weather', y='cnt', title='Daily rentals by weather', **weather_options)
        scatter = px.scatter(
            selection, x='temperature_c', y='cnt', hover_data=['date'],
            title='Temperature and daily rentals', opacity=0.65, **weather_options
        )
        monthly = selection.groupby('month', as_index=False).agg(
            average_rentals=('cnt', 'mean'), days=('cnt', 'size')
        )
        trend = px.line(
            monthly, x='month', y='average_rentals', markers=True, hover_data=['days'],
            title='Monthly average daily rentals',
            labels={'month': 'Month', 'average_rentals': 'Average rentals per day', 'days': 'Days in average'}
        )
        trend.update_traces(line_color='#126B70')
        figures = [histogram, box, scatter, trend]
        for figure in figures:
            figure.update_layout(template='plotly_white', height=380)
            if selection.empty:
                figure.data = ()
                figure.add_annotation(text='No days match this selection.', x=0.5, y=0.5, xref='paper', yref='paper', showarrow=False)
        return sample, *figures

    return app


data = pd.read_csv(Path(__file__).resolve().parent / 'data' / 'bike_sharing_daily.csv')
app = build_dashboard(data)
server = app.server

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8055, debug=False)
