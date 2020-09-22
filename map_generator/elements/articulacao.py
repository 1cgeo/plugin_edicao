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

from .map_utils import MapParent
class Articulacao(MapParent):
	def __init__(self):				
		self.customMode = True
		self.gridMode = True
		self.group_name = 'articulacao'
		self.mapItem = None
		self.folder_estilos = os.path.join(os.path.dirname(os.path.dirname(__file__)),'estilos','articulacao')

	def make(self,composition, grid_layer, selected_feature, gridMode, showLayers):
		# Deletando as variaveis
		self.deleteGroups(['articulacao'])
		map_layers = []
		
		articulacaoGroup_node = QgsLayerTreeGroup('articulacao')		
		articulacaoGroup_node.setItemVisibilityChecked(False)

		layer_moldura_mi, moldura_layer_name = self.addLayerMoldura_v2(grid_layer)
		map_layers.append(layer_moldura_mi.id())

		# Adicionamos o layer ao mapa e ao grupo 
		QgsProject.instance().addMapLayer(layer_moldura_mi, False)
		articulacaoGroup_node.addLayer(layer_moldura_mi)
		

		# Seleciona a articulação central e a extensão do mapa
		self.setLayerROI(grid_layer)
		
		map_extent = self.getExtentFromCenter(selected_feature, layer_moldura_mi)				
		# map_extent = self.getExtentFromGrid()
		
		# Adicionamos a simbologia
		self.setSymbol(selected_feature,  layer_moldura_mi)								

		if not gridMode:							
			self.setLayerROI(grid_layer)

			style_file = os.path.join(self.folder_estilos, 'moldura_feature_carta_especial_v3.qml')
			self.loadStyleToLayer(self.layer_roi, style_file)				
		
		# Atualiza o map item
		self.specialMapUpdateMapItem(composition, map_extent, layer_moldura_mi)	

		
		if showLayers:
			root = QgsProject.instance().layerTreeRoot()								
			root.addChildNode(articulacaoGroup_node)
		return map_layers

	def addLayerMoldura_v2(self, grid_layer):		
		layer_file = ''			
		moldura_layer_name = 'moldura_articulacao'
		feats = [feat for feat in grid_layer.getFeatures()]
		epsg = grid_layer.crs().postgisSrid()
		self.layer_moldura_mi = QgsVectorLayer("Polygon?crs=epsg:{epsg}".format(epsg=epsg),moldura_layer_name, "memory")
		mem_layer_data = self.layer_moldura_mi.dataProvider()
		attr = grid_layer.dataProvider().fields().toList()
		mem_layer_data.addAttributes(attr)
		self.layer_moldura_mi.updateFields()
		mem_layer_data.addFeatures(feats)
		QgsProject.instance().addMapLayer(self.layer_moldura_mi, False)
		style_file = os.path.join(self.folder_estilos, 'articulacao_especial_25k_v6.qml')
		if self.scale ==250:
			style_file = os.path.join(self.folder_estilos, 'articulacao_especial_25k_v6_250.qml')
		self.layer_moldura_mi.loadNamedStyle(style_file)
		self.layer_moldura_mi.triggerRepaint()
		return self.layer_moldura_mi, moldura_layer_name


	def getExtentFromCenter(self, selectedFeature, layer_moldura_mi):		
		selection_ids = []
		
		feature_of_center = None
		id_feature_of_center = None		
		feat_centroid = selectedFeature.geometry().centroid()
		for moldura_feature in layer_moldura_mi.getFeatures():
			if moldura_feature.geometry().contains(feat_centroid): 
				feature_of_center = moldura_feature
				selection_ids.append(id_feature_of_center)
		# Bound
		bounding = []			
		feature_of_center_geometry_bound = feature_of_center.geometry().buffer(0.05,0)
		for moldura_feature in layer_moldura_mi.getFeatures():
			if moldura_feature.geometry().intersects(feature_of_center_geometry_bound):            
				bounding.append(moldura_feature.geometry().boundingBox())
		map_extent = bounding[0]
		if len(bounding) > 1: 
			for estado_bound in bounding[1:]:
				map_extent.combineExtentWith(estado_bound)
		return map_extent

	def getExtentFromGrid(self, grid_layer):
		selectedFeature = grid_layer.selectedFeatures()[0]
		feature_of_center = selectedFeature
		self.mi = feature_of_center['inom']

		bounding = []
		for moldura_feature in grid_layer.getFeatures():
			if moldura_feature.geometry().intersects(feature_of_center.geometry()):            
				bounding.append(moldura_feature.geometry().boundingBox())
		map_extent = bounding[0]
			
		if len(bounding) > 1: 
			for estado_bound in bounding[1:]:
				map_extent.combineExtentWith(estado_bound)		
		return map_extent


	def setSymbol(self, selected_feature, layer_moldura_mi):
		symbol = QgsSymbol.defaultSymbol(layer_moldura_mi.geometryType())
		renderer = QgsRuleBasedRenderer(symbol)
		root_rule = renderer.rootRule()

		# Regra para o mi analisado
		mi_rule = root_rule.children()[0].clone()
		field = "inom"
		# value = self.mi
		value = selected_feature[field]
		expression = ' \"{}\" =  \'{}\''.format(field, value)
		mi_rule.setFilterExpression(expression)
		mi_rule.symbol().setColor(QColor(213,242,213))
		root_rule.appendChild(mi_rule)

		expression = 'ELSE'
		neighbor_rule = root_rule.children()[0].clone()
		neighbor_rule.setFilterExpression(expression)
		neighbor_rule.symbol().setColor(QColor("white"))
		root_rule.appendChild(neighbor_rule)
		root_rule.removeChildAt(0)

		layer_moldura_mi.setRenderer(renderer)
		layer_moldura_mi.triggerRepaint()

	def specialMapUpdateMapItem(self, composition, map_extent, layer_moldura_mi, mapItem=None):
		if mapItem is None:
			mapItem = composition.itemById("map_articulacao")
		if mapItem is not None:	
			mapSize = mapItem.sizeWithUnits()
			mapItem.setFixedSize(mapSize)
			mapItem.setExtent(map_extent)	
			if self.gridMode:	
				mapItem.setLayers([ layer_moldura_mi])
			else:
				mapItem.setLayers([ layer_moldura_mi, self.layer_roi])
			mapItem.refresh()