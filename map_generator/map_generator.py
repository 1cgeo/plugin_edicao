
from qgis.core import QgsProject, QgsCoordinateReferenceSystem

from gridGenerator.gui.gridAndLabelCreator import GridAndLabelCreator

from .elements.MiniMapCoordAndOthers import MiniMapCoordAndOthers
from .elements.escala_carta import EscalaCarta as HandleScale
from .elements.localizacao import Localizacao
from .elements.divisao import Divisao
from .elements.articulacao import Articulacao
from .elements.map_info import HtmlData
from .elements.minimap import MiniMap
from .elements.map import Map
from .elements.handle_diagram import HandleAngles
from .elements.map_utils import MapParent
from .elements.map_identification import editMapName
from .elements.map_identification import replaceLabelRegiao
from .elements.map_index.map_index import UtmGrid
from .elements.qrcode_picture import create_qrcode_from_feature, replace_qrCode
from .utils import MapTools

class MapManager(MapTools):
	def __init__(self, iface, dlg, GLC):
		super().__init__(iface, dlg)	
		self.mc = MapParent()	
		self.GLC = GLC
		self.map_height = 570-15*2 # milimiters		
		self.epsg_selected = False
		self.scale_selected = False		
		self.utm_grid = UtmGrid()
		
	def set_products_parameters(self, products_parameters):
		self.products_parameters = products_parameters
	
	def setElementsConfig(self, product):
		self.mi_attr = 'mi'
		self.inom_attr = 'inom'
		self.nome_attr = 'nome'
		self.escala_attr = 'escala'
		self.feature_selection_mode = 'json' # layer		
				
		self.map.setGridAndLabelParameters(**self.products_parameters[product]['grid'])
		self.map.setMapSize(588,588)
				
		self.articulacao.setGridMode(True)								
				
	def create_map_instances(self):
		# Map
		self.map = Map(self.iface, self.GLC)		
		# Minimapa
		self.miniMap = MiniMap()
		# Coordenadas do Minimapa
		self.miniMapCoordAndOthers = MiniMapCoordAndOthers()
		# Divisao			
		self.divisao = Divisao()
		# Localização
		self.localizacao = Localizacao()
		# Articulação		
		self.articulacao = Articulacao()
		# Diagrama de convergência e declinação
		self.handle_angles = HandleAngles(self.iface)				
		# Dados de info tecnica e orto
		self.htmlData = HtmlData()
		# Dados de escala
		self.dados_de_escala = HandleScale()

	# Obtem as informacoes do mapa: inom, nome, mi, escala..
	def getDefaultFeatureData(self, dict_carta):
		feature_map_extent = layer_feature_map_extent = None
		inom_text = inomen = mi = 'Especial'
		escala = '25'
		
		if 'inom' in dict_carta:
			inom_text = dict_carta['inom']
			inomen = dict_carta['inom']
			mi 		= self.utm_grid.get_MI_MIR_from_inom(inomen)
			escala = str(self.utm_grid.getScale(inomen))
			self.scale_selected = False
			layer_feature_map_extent, features_map_extent = self.utm_grid.get_new_grid_layer_from_inoms_list([inomen])
			feature_map_extent = features_map_extent[0]
		
		if 'center' in dict_carta:
			escala = int(dict_carta['escala'])/1000 # transformar para 250000
			center = dict_carta['center']
			longitude = center['longitude']
			latitude = center['latitude']
			inomen = self.utm_grid.get_INOM_from_lat_lon(longitude, latitude, escala)	
			layer_feature_map_extent, features_map_extent = self.create_layer_from_center_and_escala(longitude, latitude,escala)
			self.scale_selected = True

		self.inom 		= inom_text
		self.mi 		= mi					
		self.hemisferio = inomen[0]
		self.fuso 		= inomen[3:5]				
		self.selectedFeature_id = 'id'
		self.selectEpsg(self.hemisferio, self.fuso)				
		self.scale 	= int(escala)
		return feature_map_extent, layer_feature_map_extent
	
	def getScaleHemisferioFusoFromInom(self, inom):
		hemisferio = inom[0]
		fuso 		= inom[3:5]							
		scale 	= self.utm_grid.getScale(inom)
		return scale, hemisferio, fuso

	def getFirstConnection(self, caminhos_json_carta):
		success = True
		uri = None
		if len(caminhos_json_carta)>0:
			for caminho_json_carta in caminhos_json_carta:				
				dict_carta = self.readJsonFromPath(caminho_json_carta)
				dict_conexao = dict_carta['banco']
				if dict_conexao != {}:
					success, uri = self.getDBConnection(dict_conexao)
					if success:
						break														
				else:
					continue
		return success, uri
			
	def createMap(self, composition, grid_layer, selected_feature, layers, showLayers=False):
		map_layers = []
		self.map.setEPSG(self.hemisferio, self.fuso)
		self.map.setCustomMode()
		self.map.setSpacingFromScale(self.scale)				
		map_layers = self.map.make(composition, grid_layer, selected_feature, layers, showLayers)
		return map_layers

	def createGridLayer(self, inom):		
		grid_layer, center_feat = self.utm_grid.get_neighbors_inom(inom)
		grid_layerId = grid_layer.id()
		QgsProject.instance().addMapLayer(grid_layer, False)
		return grid_layer, grid_layerId, center_feat

	def createAll(self, composition, nome, inomen,  map_extent_feature, layer_feature_map_extent, layers, showLayers = False):		
		# Store temporary map layers ids
		ids_maplayers = []
			
		ids_maplayers.append(layer_feature_map_extent.id()) # Add layer feature map extent to remove after

		QgsProject.instance().setCrs(QgsCoordinateReferenceSystem(4326,QgsCoordinateReferenceSystem.EpsgCrsId))			
		if composition.itemById("the_map") is not None:
			ids_maplayers.extend(self.createMap(composition, layer_feature_map_extent, map_extent_feature, layers, showLayers))

		# Mini mapa
		if composition.itemById("map_miniMap") is not None:			
			ids_maplayers.extend(self.miniMap.make(composition, map_extent_feature, layers, showLayers))
			self.miniMapCoordAndOthers.make(composition, map_extent_feature, addDataToMarginal = False)	

		# Adicionando as imagens nos ids para remover
		ids_maplayers.extend(layers['id_images'])

		# Mapa de Divisão
		if composition.itemById("map_divisao") is not None:
			self.divisao.setEPSG(self.hemisferio, self.fuso)
			ids_maplayers.extend(self.divisao.make(composition, map_extent_feature, showLayers))

		# Mapa de Articulação		
		if composition.itemById("map_articulacao") is not None: 			
			self.articulacao.setScale(self.scale)
			gridMode = True				
			ids_maplayers.extend(self.articulacao.make(composition, inomen, layer_feature_map_extent, gridMode, showLayers))					

		# Diagrama de convergência e declinação				
		self.handle_angles.make(composition, map_extent_feature)		

		# Dados de escala e nome
		self.dados_de_escala.setScale(self.scale*1000)		
		self.dados_de_escala.changeScaleLabels(composition)	
		editMapName(composition, nome, self.mi, self.inom)

		if composition.itemById("label_regiao")	is not None:
			pass

		# Mapa de Localização
		if composition.itemById("map_localizacao") is not None:
			adaptacaoNome = False
			mapLayers_loocalizacao = self.localizacao.make(composition, map_extent_feature, adaptacaoNome, showLayers)
			ids_maplayers.extend(mapLayers_loocalizacao)	
			regioes = self.localizacao.regioes			
			replaceLabelRegiao(composition, regioes)	

		# Generating qrcode
		camadas_adicionar = ["localidades", "mosaico_topograficas"]
		success, path_qrCode = create_qrcode_from_feature(map_extent_feature, str(self.scale), camadas_adicionar, nome )
		replace_qrCode(composition, path_qrCode)

		# Exporta os mapas				
		if not showLayers:
			self.exportMap(composition)

		# Add grid layer
		#ids_maplayers.extend([grid_layer.id()])
		
		if not showLayers:
			self.deleteMaps(ids_maplayers, True)						
			# delete_file(path_qrCode) # deleting qrCode