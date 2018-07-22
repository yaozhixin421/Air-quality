#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Mon Jul 16 12:25:23 2018

@author: k1641900
"""
# =============================================================================
# https://automating-gis-processes.github.io/CSC18/lessons/L5/advanced-bokeh.html
# https://bokeh.pydata.org/en/latest/docs/user_guide/tools.html
# https://stackoverflow.com/questions/40226189/bokeh-is-not-rendering-properly-multipolygon-islands-from-geojson
# https://stackoverflow.com/questions/45144032/how-daterangeslider-in-bokeh-works
# https://stackoverflow.com/questions/49028057/update-geojsondatasource-in-bokeh
# https://github.com/bokeh/bokeh/blob/master/examples/app/sliders.py
# =============================================================================


import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
from shapely.ops import cascaded_union

from datetime import date,datetime,timedelta
from bokeh.io import curdoc
from bokeh.layouts import widgetbox,layout,row
from bokeh.models import GeoJSONDataSource,LinearColorMapper,ColorBar
from bokeh.models.widgets import Slider, TextInput, DateSlider
from bokeh.plotting import figure
from bokeh.palettes import YlOrRd6 as palette


##############################################################################

#map
lnd_bor = gpd.read_file('london.geojson', driver='GeoJSON')
lnd_bor = lnd_bor.to_crs(epsg=27700)

#London boundary
London=[]
for i in range(len(lnd_bor)):
    London.append(lnd_bor.geometry[i])
London=cascaded_union(London)

#point
df=pd.read_csv('sample.csv')
geometry=[Point(xy) for xy in zip(df.longitude,df.latitude)]
df=df.drop(['longitude','latitude'],axis=1)
crs={'init':'epsg:4326'}
gdf=gpd.GeoDataFrame(df,crs=crs,geometry=geometry)
gdf=gdf.to_crs(lnd_bor.crs)

#selete(London)
gdf=gdf[gdf.geometry.within(London)]


#TimeRange
starttime_timestamp=str(int(gdf['utc_recordedtimestamp_hh'].min()))[:-3]
endtime_timestamp=str(int(gdf['utc_recordedtimestamp_hh'].max()))[:-3]
start_date=datetime.utcfromtimestamp(int(starttime_timestamp)).date()
end_date=datetime.utcfromtimestamp(int(endtime_timestamp)).date()

#PointInPloy
PointInPoly=gpd.sjoin(gdf,lnd_bor,op='within')

#Average CO
lnd_bor['Ave_CO']=0.0

#calculate average CO each day
def select_date(given_date):
    selected1=PointInPoly[PointInPoly.recordedlocaldatetime_hh.str[:4].astype(int)==given_date.year]
    selected2=selected1[selected1.recordedlocaldatetime_hh.str[5:7].astype(int)==given_date.month]
    selected3=selected2[selected2.recordedlocaldatetime_hh.str[8:10].astype(int)==given_date.day]
    return selected3

borough=pd.DataFrame(lnd_bor.name)
d=start_date
while d<=end_date:
    
    table=select_date(d)
    ave_co=table.groupby('name').agg({'cofiltered':'mean'}).reset_index(drop=False)
    borough=borough.join(ave_co.set_index('name'),on='name')
    borough=borough.rename(columns={'cofiltered':d})
    d+=timedelta(days=1)

borough=borough.fillna(0)


# Set up data
source=GeoJSONDataSource(geojson=lnd_bor.to_json())
lnd_bor=lnd_bor.join(borough.set_index('name'),on='name')

def make_plot(mapper):
    mapper.low_color='white'
    mapper.high_color='red'
    p=figure(toolbar_location=None,tools='',title='A test map',plot_height=600, plot_width=800,x_axis_location=None, y_axis_location=None)
    p.grid.grid_line_color = None
    color_bar=ColorBar(color_mapper=mapper,location=(0,0))
    p.patches(
            'xs','ys',
            fill_color={'field': 'Ave_CO', 'transform': mapper}, 
            line_color='white',
            source=source
            )
    p.add_layout(color_bar,'right')
    return p

palette.reverse()
plot=make_plot(LinearColorMapper(palette=palette,low=-2,high=15))

# Set up widgets
#text=TextInput(title="Title", value='my sine wave')
Date=DateSlider(title="Date",start=start_date, end=end_date, value=start_date, step=1)

# Set up callbacks
# =============================================================================
# def update_title(attrname, old, new):
#     plot.title.text = text.value
# 
# text.on_change('value', update_title)
# =============================================================================
# =============================================================================
# group=gdf.groupby('county')
# sample=group.agg({'cofiltered':'mean'}).reset_index(drop=False)
# lnd_bor.join(sample.set_index('county'),on='name')
# 
# pd.DataFrame(lnd_bor.name).join(sample.set_index('county'),on='name')
# =============================================================================


def update_data(attrname,old,new):

    co_now=lnd_bor[['name','geometry',Date.value]]
    co_now=co_now.rename(columns={Date.value:'Ave_CO'})
    gjson=co_now.to_json()
    source.geojson=gjson
    
    
Date.on_change('value', update_data)


# Set up layouts and add to document
inputs = widgetbox(Date)

curdoc().add_root(row(inputs, plot))
curdoc().title = "London"

