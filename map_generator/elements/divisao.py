# -*- coding: utf-8 -*-
"""
/***************************************************************************
 EditionPlugin
                                 A QGIS plugin
 This plugin helps the edition of maps.
                              -------------------
        begin                : 2020-09-13
        git sha              : $Format:%H$
        copyright            : (C) 2020 by Ronaldo Martins da Silva Junior
        email                : ronaldo.rmsjr@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.core import *
from qgis.gui import *
import qgis  # NOQA
from qgis.core import *
from qgis.gui import *
#subprocess.check_call(['pip', 'install', 'pyshp'])
from qgis.PyQt import sip
import os
import re
from datetime import datetime
from PyQt5.QtGui import QColor
from PyQt5.QtGui import * 
from PyQt5.QtCore import QSettings, QVariant
from qgis.core import QgsApplication
import math
import json
import shapely.wkt
import shapely.geometry
from .map_utils import MapParent

class Divisao(MapParent):
	def __init__(self):			
		self.itemname_tableMunicipios = 'label_divisao_municipios'
		self.mapItem = None
		self.folder_estilos = os.path.join(os.path.dirname(os.path.dirname(__file__)),'estilos','divisao')
		self.setVariables()

	def setVariables(self):
		self.file_basehtmltable = 'divisao.html'
		self.n_maxlines = 6
		#self.itemname_tableMunicipios = 'label_divisao_municipios'

	def make(self, composition, selected_feature):
		# Deletando as variaveis
		self.deleteGroups(['divisao'])
		map_layers = []
		
		# Adiciona os layers de municipios, estado e limite internacional
		divisaoGroup_node = QgsLayerTreeGroup('divisao')			
		municipios_layer, estados_layer, internacional_layer = self.createLayersGroup()
		map_layers.extend([municipios_layer.id(), estados_layer.id(), internacional_layer.id()])

		# Cria o layer da área do mapa
		grid_bound = selected_feature.geometry().boundingBox()
		grid_rectangleLayer = self.createGridRectangle(grid_bound, 'auxiliar_divisao')
		map_layers.append(grid_rectangleLayer.id())

		# Get map extent for intersections
		map_extent = self.getExtent(grid_bound, selected_feature)
		municipios_datalist ,sorted_municipios = self.getIntersections(municipios_layer, map_extent[0], selected_feature)

		# Set styles and html table data for municipios que intersectam
		self.setStyles(municipios_layer, municipios_datalist , sorted_municipios)
		html_tabledata = self.customcreateHtmlTableData(sorted_municipios)
		self.setMunicipiosTable(composition,  html_tabledata)		

		for layer in [ grid_rectangleLayer, internacional_layer, estados_layer, municipios_layer]:
			QgsProject.instance().addMapLayer(layer, False)
			divisaoGroup_node.addLayer(layer)
		
		divisaoGroup_node.setItemVisibilityChecked(False)		
		root = QgsProject.instance().layerTreeRoot()		
		#root.addChildNode(divisaoGroup_node)

		# Update map
		layers_to_show = [grid_rectangleLayer, internacional_layer, estados_layer, municipios_layer ] # baixo -> cima
		self.updateMapItem(composition, map_extent[0], layers_to_show)
		return map_layers		

	def createLayersGroup(self):
		layer_name = 'municipios'
		uri =  os.path.join(os.path.dirname(os.path.dirname(__file__)),'limites','municipios_2019.shp')
		style_file = os.path.join(self.folder_estilos, 'limite_municipal.qml')
		municipios_layer = QgsVectorLayer(uri,layer_name,'ogr')
        
		if (municipios_layer.isValid()):
			municipios_layer.loadNamedStyle(style_file)
			# QgsProject.instance().addMapLayer(municipios_layer)
		
		estado_uri = os.path.join(os.path.dirname(os.path.dirname(__file__)),'limites','estados_2019.shp')
		estado_style_file = os.path.join(self.folder_estilos, 'limite_estadual_vf.qml')
		estados_layer = QgsVectorLayer(estado_uri,'limite_estado','ogr')
		estados_layer.loadNamedStyle(estado_style_file)		
		
		internacional_uri =  os.path.join(os.path.dirname(os.path.dirname(__file__)),'limites','internacional.shp')
		internacional_style_file = os.path.join(self.folder_estilos, 'limite_internacional_vf.qml')
		internacional_layer = QgsVectorLayer(internacional_uri,'limite_internacional','ogr')
		internacional_layer.loadNamedStyle(internacional_style_file)

		return municipios_layer, estados_layer, internacional_layer

	def getExtent(self, grid_bound, selected_feature):
		self.ext = []				
		x_min = grid_bound.xMinimum()
		x_max = grid_bound.xMaximum()
		delta = round(abs((x_max-x_min)*60))
		angle_spliter = delta			
		centroide = selected_feature.geometry().centroid()
		x = (centroide.asPoint().x())
		x_min = x -(1/60)*angle_spliter
		x_max = x +(1/60)*angle_spliter
		y = (centroide.asPoint().y())
		y_min = y -(1/60)*angle_spliter
		y_max = y +(1/60)*angle_spliter
		self.ext.append(qgis.core.QgsRectangle(x_min,y_min,x_max,y_max))
		return self.ext

	def getDistancePointPolygon(self, point, polygonGeometry):
		distance = QgsDistanceArea()			
		distance.setEllipsoid('WGS84')
		m = round(distance.measureLine(geomOne, geomTwo),2)
		return m

	def getDistance(self, geomOne, geomTwo):
		distance = QgsDistanceArea()			
		distance.setEllipsoid('WGS84')
		m = round(distance.measureLine(geomOne, geomTwo),2)
		return m

	def checkRadiusPoleForLabel(self, feature_municipio, moldura_geometry, moldura_area):	
		show = True
		max_radius_per_map_area = 2300
		intersection_geometry = feature_municipio.geometry().intersection(moldura_geometry)
		# mudando o epsg
		crsSrc = QgsCoordinateReferenceSystem(4326)    # WGS 84
		crs_moldura = QgsCoordinateReferenceSystem(int(self.epsg), QgsCoordinateReferenceSystem.EpsgCrsId)  # WGS 84 / UTM zone 33N
		geom_transformation = QgsCoordinateTransform(crsSrc, crs_moldura, QgsProject.instance())
		intersection_geometry.transform(geom_transformation)
		pole = intersection_geometry.poleOfInaccessibility(10)
		radius = pole[1]
		radius_per_map_area = radius/moldura_area
		if radius_per_map_area < max_radius_per_map_area :
			show = False		
		return radius_per_map_area, show

	def convertPolygonToMultilineGeometry(self, moldura_geometry):
		feat_geom = moldura_geometry.asWkt()
		loaded_poly = shapely.wkt.loads(feat_geom) 
		shapely_multipoly = shapely.geometry.Polygon(loaded_poly)
		shapely_multipoly_boundary = shapely_multipoly.boundary
		boundary_polyline = QgsLineString()
		boundary_polyline.fromWkt(shapely_multipoly_boundary.wkt)
		boundary_geom = QgsGeometry(boundary_polyline)
		return boundary_geom

	def getIntersections(self, municipios_layer, map_extent, selected_feature):
		max_municipios = 27
		attr_nome = 'nome_abre'
		d = QgsDistanceArea()
		extent_geometry = QgsGeometry.fromRect(map_extent)
		linhaContorno_moldura = self.convertPolygonToMultilineGeometry(extent_geometry)
		moldura_area = math.sqrt(extent_geometry.area())
		self.municipios = []
		self.municipios_ordenados = {}
		municipios_intersectam = []
		moldura_centroid = selected_feature.geometry().centroid().asPoint()
		testeGeometries = []
		for count, feature_municipio in enumerate(municipios_layer.getFeatures()):
			# municipio dentro dos limites da carta
			if feature_municipio.geometry().intersects(extent_geometry):
				if (feature_municipio[attr_nome] is not None) and (not isinstance(feature_municipio[attr_nome], QVariant)):
					municipio = (feature_municipio[attr_nome]) + ' - ' + feature_municipio['sigla_uf']					
					if municipio is not None:						
						# municipio intersecta os limites da carta
						radius_per_map_area = 'inside'
						show = True
						if feature_municipio.geometry().intersects(linhaContorno_moldura):	
							#print('intersect')												
							radius_per_map_area, show = self.checkRadiusPoleForLabel( feature_municipio, extent_geometry, moldura_area)
							testeGeometries.append(feature_municipio.geometry().intersection(extent_geometry))
						
						municipio_centroid = feature_municipio.geometry().centroid().asPoint()                    
						objeto_municipio = {    'label': municipio,
												'area':d.measureArea(feature_municipio.geometry()),
												'codigo':feature_municipio['codigo'],
												'poleOfInaccessibility': radius_per_map_area,
												'distancia_centroid':self.getDistance(moldura_centroid, municipio_centroid),
												'distancia_centroid_borda_polygon':selected_feature.geometry().centroid().distance(feature_municipio.geometry())}
						if show:							
							municipios_intersectam.append(objeto_municipio)
							self.municipios_ordenados[municipio] = d.measureArea(feature_municipio.geometry())
							self.municipios.append(municipio)
		# createIntersections_layer
		self.intersectionsLayer = self.createGridRectangleLayer('intersections_municipio', testeGeometries)
		sorted_municipios = sorted(self.municipios_ordenados, key=self.municipios_ordenados.get, reverse=True)
		newlist = sorted(municipios_intersectam, key=lambda k: k['distancia_centroid_borda_polygon'], reverse=False) 
		newlist_names = [municipio['label'] for municipio in newlist]
		sorted_municipios = newlist_names

		if len(sorted_municipios)>=max_municipios:
			sorted_municipios = sorted_municipios[0:max_municipios]

		return newlist, sorted_municipios

	def getNColums(self, n_total):
		n_columns = 1
		n_extra = n_total-18
		n_mod = n_extra % 3
		n_div = math.floor(n_extra / 3)
		initial_n_column1 = 0
		initial_n_column2 = 0
		initial_n_column3 = 0
		add_column1 = 0
		add_column2 = 0
		add_column3 = 0
		if 0 < n_total <= 6:
			initial_n_column1 = n_total
		elif 6 < n_total <= 12:
			n_columns = 2
			initial_n_column1 = 6
			initial_n_column2 = n_total-6
		elif 12 < n_total <= 18:
			n_columns = 3
			initial_n_column1 = 6
			initial_n_column2 = 6
			initial_n_column3 = n_total-12
		else:
			n_columns = 3
			initial_n_column1 = 6
			initial_n_column2 = 6
			initial_n_column3 = 6
			add_column1 = n_div + (1 if n_mod == 1 or n_mod == 2 else 0)
			add_column2 = n_div + (1 if n_mod == 2 else 0)
			add_column3 = n_div 

		n_column1 = initial_n_column1 + add_column1
		n_column2 = initial_n_column2 + add_column2
		n_column3 = initial_n_column3 + add_column3
		
		return n_columns, n_column1, n_column2, n_column3
			
	def goNextColumn(self, municipio_index, n_column1, n_column2, n_column3):
		n_municipio = municipio_index + 1    
		# nextColumn = False
		if n_municipio ==  n_column1 or n_municipio ==  n_column1 + n_column2 or n_municipio ==  n_column1 + n_column2 + n_column3:
			return True
		else: 
			return False

	def customcreateHtmlTableData(self, sorted_municipios ):		
		n_municipios = len(sorted_municipios)
		n_columns = math.ceil(n_municipios/self.n_maxlines)
		#print(n_municipios)
		#print(n_columns)
		if n_columns == 0:
			n_columns = 1
		
		step = math.ceil(n_municipios/n_columns)
		txt_file = os.path.join(os.path.dirname(os.path.dirname(__file__)),'html_auto',self.file_basehtmltable)
		#filepath = os.path.join(folder, filer)
		f = open(txt_file, "r")
		base_html = f.read()
		font_size = '0.6'
		if n_municipios > 6:
			font_size = '0.60'
		if n_municipios > 12:
			font_size = '0.60'
	
		n_columns, n_column1, n_column2, n_column3 = self.getNColums(n_municipios)
				
		# baserows_str = '<tr> {}</tr>'
		# baserows_str = '<tr> {}</tr>'
		baserows_str = '<tr {style}> {}</tr>'
		style_str = 'style="width: {value}%;"'.replace('{value}', str(round(100/n_columns ,2)))
		baserows_str = baserows_str.replace('{style}', style_str)
		# 'style="width: 50%;"'
		basecolumn_str = '<td class = "mid" >{}</td>'

		tablerow_columns = []
		tablerows_list = []	
		for municipio_index, municipio in enumerate(sorted_municipios):    
			n_municipio = municipio_index + 1 			
			cell_str = str(n_municipio) + ' - ' + municipio
			tablerow_column = basecolumn_str.format(cell_str)
			tablerow_columns.append(tablerow_column)
			if self.goNextColumn(municipio_index, n_column1, n_column2, n_column3):
				tablerow = baserows_str.format('\n'.join(tablerow_columns))
				tablerows_list.append(tablerow)
				tablerow_columns = []

		table_content = '\n'.join(tablerows_list)

		edited = base_html.format(font_size = font_size, table_data = table_content)
		return edited

	def setMunicipiosTable(self,composition,  html_tabledata):
		compositionItem = composition.itemById(self.itemname_tableMunicipios)
		if compositionItem is not None:
			compositionItem.setText(html_tabledata)
			compositionItem.setMode(QgsLayoutItemLabel.ModeHtml)
			compositionItem.refresh()

	def createRules(self, layer, symbol, renderer, label, expression, color):
		#Configure label settings
		settings = QgsPalLayerSettings()
		#settings.fieldName = "'{}'".format(str(n))
		settings.fieldName = label
		settings.Placement = QgsPalLayerSettings.OverPoint
		settings.centroidInside = True
		settings.isExpression = True
		textFormat = QgsTextFormat()
		textFormat.setColor(QColor(0,0,0,255))
		textFormat.setSize(6)

		textBuffer = QgsTextBufferSettings()
		textBuffer.setColor(QColor(255,255,255,255))
		textBuffer.setSize(0.4)
		textBuffer.setEnabled(True)
		textFormat.setBuffer(textBuffer)

		settings.setFormat(textFormat)
		#create and append a new rule
		#root = QgsRuleBasedLabeling.Rule(QgsPalLayerSettings())
		rule = QgsRuleBasedLabeling.Rule(settings)
		#rule.setDescription(fieldName)
		rule.setFilterExpression(expression)
		rule.setActive(True)
		return rule
		
	def createGridRectangle(self, grid_bound, layer_name):
		geometries = [QgsGeometry.fromRect(grid_bound)]
		grid_rectangleLayer = self.createGridRectangleLayer(layer_name, geometries)
		# Setting configuration
		if False:
			symbol = QgsSymbol.defaultSymbol(grid_rectangleLayer.geometryType())
			renderer = QgsRuleBasedRenderer(symbol)
			root_rule = renderer.rootRule()
			mi_rule = root_rule.children()[0].clone()	    
			mi_rule.symbol().setColor(QColor(171,230,171))
			mi_rule.symbol().setOpacity(0.7)		
			root_rule.appendChild(mi_rule)
			root_rule.removeChildAt(0)
			grid_rectangleLayer.setRenderer(renderer)
		else:
			style_file = os.path.join(self.folder_estilos, 'divisao_grid_bound_vf.qml')			
			grid_rectangleLayer.loadNamedStyle(style_file)		
		grid_rectangleLayer.triggerRepaint()
		return grid_rectangleLayer		

	def setStyles(self, municipios_layer, municipios_datalist, sorted_municipios):    
		#municipios_layer = QgsProject.instance().mapLayersByName('municipios')[0]
		symbol = QgsSymbol.defaultSymbol(municipios_layer.geometryType())
		renderer = QgsRuleBasedRenderer(symbol)
		root = QgsRuleBasedLabeling.Rule(QgsPalLayerSettings())
		# self.sorted_municipios = sorted(self.municipios_ordenados, key=self.municipios_ordenados.get, reverse=True)
		for count, municipio in enumerate(sorted_municipios):
			n = count + 1
			rule = self.createRules(municipios_layer, symbol, renderer,  "'{}'".format(str(n)), ' \"codigo\" = \'{}\''.format(municipios_datalist[count]['codigo']), 'black')
			root.appendChild(rule)
		rules = QgsRuleBasedLabeling(root)
		#root.setActive(True)
		municipios_layer.setLabeling(rules)
		municipios_layer.setLabelsEnabled(True)
		municipios_layer.triggerRepaint()

	def updateMapItem(self, composition, map_extent, layers_to_show):	
		if self.mapItem is None:
			self.mapItem = composition.itemById("map_divisao")
		if self.mapItem is not None:	
			self.mapItem.setExtent(map_extent)
			self.mapItem.refresh()		
			self.mapItem.setLayers(layers_to_show) 
			self.mapItem.refresh()
