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
# qgis libraris
from qgis.core import *
from qgis.gui import *

# PyQT5 libraries
from PyQt5.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QAbstractTableModel, Qt, QVariant
from PyQt5.QtGui import QIcon, QFont, QColor, QImage, QPainter
from PyQt5.QtWidgets import QAction, QTableView

# Other libraries
from datetime import datetime as dt
from collections import Counter
import datetime
import time
import math
import os
import shapely.wkt
import shapely.geometry
import json
import codecs
from .elements.map_index.map_index import UtmGrid
class MapTools:
    def __init__(self, iface, dlg):
        self.iface 			= iface        
        self.dlg 			= dlg 
        self.utm_grid		= UtmGrid()
        self.selectedMapItem = None         

    def readJsonFromPath(self, path_json):        
        # json_file = open(path_json)
        json_file = codecs.open(path_json, 'r', 'utf-8-sig')
        #json_str = json_file.read()
        #json_data = json.loads(json_str)
        json_data = json.load(json_file)
        json_file.close()
        return json_data
    
    def create_layer_from_center_and_escala(self, longitude, latitude,escala):        
        x = longitude
        spacing_x = self.utm_grid.getSpacingX(escala)
        x_min = x - spacing_x/2
        x_max = x + spacing_x/2
        y = latitude
        spacing_y = self.utm_grid.getSpacingX(escala)
        y_min = y - spacing_y/2
        y_max = y + spacing_y/2
        rect = qgis.core.QgsRectangle(x_min,y_min,x_max,y_max)
        geom = QgsGeometry.fromRect(rect)
        layer, feat = self.create_layer_from_geometry('map_extent', geom)
        return layer, feat

    def create_layer_from_geometry(self, name, geom, layerType='Multipolygon', crsAuthId='4326'):
        layer = QgsVectorLayer('%s?crs=EPSG:%s'% (layerType, crsAuthId), name, 'memory')
        if not layer.isValid():
            return None
        else:
            provider = layer.dataProvider()
            fields = QgsFields()
            fields.append(QgsField('inom', QVariant.String))
            fields.append(QgsField('mi', QVariant.String))
            fields.append(QgsField('id', QVariant.String))
            provider.addAttributes(fields)
            layer.updateFields()

            layer.startEditing()            
            fet = QgsFeature(fields)
            fet['id'] = '1'
            fet.setGeometry(geom)
            feats.append(fet)
            provider.addFeatures([fet])

            # Commit changes
            layer.commitChanges()
            return layer, fet    

    def update_qpt_variables(self, composition, novo_valor, chave='edition_folder'):        
        if 'variableNames' in composition.customProperties():
            chaves = composition.customProperty('variableNames')
            valores = composition.customProperty('variableValues')
            index_of_key = -1
            if chave in chaves:
                index_of_key = chaves.index(chave)
                valores[index_of_key] = novo_valor
                composition.setCustomProperty('variableValues', valores)
            else:
                chaves.append(chave)
                valores.append(novo_valor)
                composition.setCustomProperty('variableNames', chaves)
                composition.setCustomProperty('variableValues', valores)
        else:
            composition.setCustomProperty('variableNames', [chave] )
            composition.setCustomProperty('variableValues', [novo_valor])

    def selectEpsg(self, hemisferio, fuso):		
        self.epsg_selected = True				
        self.hemisferio = hemisferio
        self.fuso = int(fuso)
        epsg = "319"
        if self.hemisferio == 'N':
            epsg = epsg + str(72 + self.fuso-18)
        elif self.hemisferio == 'S':
            epsg = epsg + str(78 + self.fuso-18)
        self.epsg = int(epsg)

    def getDictWithEqualKeys(self, list_of_dict, dict_to_check, equal_keys):
        for dict_in_list in list_of_dict:
            for key in equal_keys:
                if dict_to_check[key] != dict_in_list[key]:
                    continue
            return dict_in_list        

    def getMapLayers(self, connectedUri,  list_dict_maptables, list_dict_minimaptables, tipo_produto, escala):		
        map_layers_db, map_layersId_db = self.getLayersFromDB(connectedUri,  list_dict_maptables, "carta",  tipo_produto, escala)
        minimap_layers_db, minimap_layersId_db = self.getLayersFromDB(connectedUri, list_dict_minimaptables, "carta_mini",   tipo_produto, escala)
        return map_layers_db, map_layersId_db, minimap_layers_db, minimap_layersId_db

    def getDBConnection(self,dict_conexao):
        host = dict_conexao['servidor']
        port = dict_conexao['porta']
        db_name = dict_conexao['nome']
        
        uri = QgsDataSourceUri()
        # assign this information before you query the QgsCredentials data store
        uri.setConnection(host, port, db_name, None, None)
        connInfo = uri.connectionInfo()
        (success, user, passwd) = QgsCredentials.instance().get(connInfo, None, None)
        if success:
            uri.setPassword(passwd)
            uri.setUsername(user)
            return success, uri
        else:
            return success, None

    def getLayer(self, connectedUri, dict_layer, grupo):		
        schema = dict_layer['schema']
        tablename = dict_layer['tabela']
        # geometrycol = dict_layer['geometrycol']
        geometrycol = 'geom'
        layername = tablename + '_' + grupo 
        
        # uri.setDataSource('', '(' + sql + ')', 'geom', '', 'id')
        connectedUri.setDataSource(schema, tablename, geometrycol)
        
        layer = QgsVectorLayer(connectedUri.uri(False), layername, "postgres")		
        return layer

    def getLayersFromDB(self, connectedUri, tables_dict, grupo, tipo_produto, escala):
        layers_db = []
        layersId_db = []        
        style_folder = os.path.join(os.path.dirname(__file__),'produtos', tipo_produto,'estilos',escala, grupo)
        if connectedUri is not None:
            for dict_layer in tables_dict:			
                layer_db = self.getLayer(connectedUri, dict_layer, grupo)   
                if (layer_db.isValid()):
                    QgsProject.instance().addMapLayer(layer_db, False)         			
                    style_file = os.path.join(style_folder, dict_layer['tabela'] + '.qml'  )
                    if os.path.exists(style_file):
                        layer_db.loadNamedStyle(style_file)
                        layer_db.triggerRepaint()
                    layers_db.append(layer_db)
                    layersId_db.append(layer_db.id())
        return layers_db, layersId_db

    def checkSelectedLayerFeatures(self, layer):
        error = False
        text_message = ""
        # Check if moldura layer has only one Feature
        if layer:
            roi_selected_features = layer.selectedFeatureCount()
            if roi_selected_features == 0:
                text_message = "Sem feições selecionadas da camada moldura. A camada moldura deve possuir uma feição selecionada."
                error = True
            if error:
                self.iface.messageBar().pushMessage("Gerar Area:", text_message, level=Qgis.Info, duration=3)
                return False
            else:
                return True
        else:
            self.iface.messageBar().pushMessage("Layer de moldura não selecionado.", text_message, level=Qgis.Info, duration=3)
            return False

    def exportMap(self, composition):        
        basename = self.mi + '_' + self.inom 
        pdf_filename = os.path.join(self.saveFolder,basename + ".pdf") 
        tiff_filename = os.path.join(self.saveFolder, basename + ".tif")
        exporter = QgsLayoutExporter(composition)        
        exportPdf = True
        
        if exportPdf:
            pdf_settings = QgsLayoutExporter.PdfExportSettings()            
            pdf_settings.rasterizeWholeImage = True
            pdfExport_result = exporter.exportToPdf(pdf_filename, pdf_settings)				
        if self.dlg.checkBox_exportar_geotiff.isChecked():
            imageExport_result = exporter.exportToImage(tiff_filename, QgsLayoutExporter.ImageExportSettings())		        
        del exporter
        # QgsProject.instance().setCrs(QgsCoordinateReferenceSystem(int(self.epsg),QgsCoordinateReferenceSystem.EpsgCrsId))

    def removeCreationDataGroups(self, map_groups = ['localizacao' , 'articulacao', 'map','minimap',  'divisao', 'localizacao_nome_estado']):
        root = QgsProject.instance().layerTreeRoot()
        for group in map_groups:
            group_localizacao = root.findGroup(group)
            root.removeChildNode(group_localizacao)

    def reproject(self, origin_path, target_path, source_epsg , target_epsg=4674):
        source_path = " -of GTiff " + origin_path				            
        sc_target_epsg = " -t_srs EPSG:" + str(target_epsg)
        #cmd = "gdalwarp  -co COMPRESS=LZW -overwrite -s_srs EPSG:" + \        
        cmd = "gdalwarp  -co COMPRESS=JPEG -co \"TILED=YES\" -overwrite -s_srs EPSG:" + \
        str(source_epsg) + \
        sc_target_epsg + \
        source_path + \
        " " + \
        target_path										
        os.system(cmd)
        
    def remove_alpha_band(self, origin_path, target_path):
        #cmd = "gdal_translate -b 1 -b 2 -b 3 -co COMPRESS=JPEG " + \
        cmd = "gdal_translate -b 1 -b 2 -b 3 -co COMPRESS=JPEG -co \"TILED=YES\"  " + \
        origin_path + \
        " " + \
        target_path										
        os.system(cmd)

    def convert_ycbcr(self, origin_path, target_path):            
        cmd = "gdal_translate -co COMPRESS=JPEG -co \"TILED=YES\" -co PHOTOMETRIC=YCBCR " + \
        origin_path + \
        " " + \
        target_path										
        os.system(cmd)

    def convert(self, origin_path, target_path):
        cmd = "gdal_translate  -co PHOTOMETRIC=YCBCR  " + \
        origin_path + \
        " " + \
        target_path										
        os.system(cmd)

    def reprojectTiffs(self):
        folder_reprojetado = os.path.join(self.saveFolder, 'padrao_bdgex')
        os.mkdir(folder_reprojetado)
        for file in os.listdir(self.saveFolder):
            if file.endswith(".tif"):				
                rasterPath = os.path.join(self.saveFolder, file)
                rlayer = QgsRasterLayer(rasterPath, "reproject")
                if not rlayer.isValid():
                    print("Layer failed to load!")
                CRS = rlayer.crs()
                source_epsg = CRS.postgisSrid()
                del rlayer

                rasterSource = rasterPath
                filename_without_ext = (file.split('.'))[0]
                caminho_reprojetado = os.path.join(folder_reprojetado,filename_without_ext + '_reprojetado.tif') 
                self.reproject(rasterPath, caminho_reprojetado, source_epsg ,4674)
                caminho_rgb = os.path.join(folder_reprojetado, filename_without_ext + '_rgb.tif') 
                self.remove_alpha_band(rasterPath, caminho_rgb)

                target_path  = os.path.join(folder_reprojetado, filename_without_ext + '.tif') 
                self.convert_ycbcr(caminho_rgb, target_path)
                os.remove(caminho_reprojetado)
                os.remove(caminho_rgb)

    def createTifPdfFolders(self, saveFolder):        
            os.mkdir(saveFolder)
            
    def deleteMaps(self, ids_maplayers, remove=False):	
        if remove:	
            for id_mapLayer in ids_maplayers:
                QgsProject.instance().removeMapLayer(id_mapLayer)

    def changeProjectVariable(self, str_escala, mi):
        project = QgsProject.instance()
        scope = QgsExpressionContextUtils.projectScope(project)
        QgsExpressionContextUtils.setProjectVariable(project, "escala", str_escala)
        QgsExpressionContextUtils.setProjectVariable(project, "mi", mi)
        self.iface.mapCanvas().refreshAllLayers() 
