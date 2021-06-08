import datetime
import os
import xml.etree.ElementTree as et
from pathlib import Path

from .map_utils import MapParent, copyQptToCompositor

curvas = {
    "25":	{
        "auxiliar": "5",
        "normal": "10",
        "mestra": "50"
    },
    "50":	{
        "auxiliar": "10",
        "normal": "20",
        "mestra": "100"
    },
    "100": {
        "auxiliar": "25",
        "normal": "40",
        "mestra": "200"
    },
    "250": {
        "auxiliar": "50",
        "normal": "100",
        "mestra": "500"
    },
    "1000": {
        "auxiliar": "100",
        "normal": "200",
        "mestra": "500"
    }
}

class HtmlData(MapParent):
    def __init__(self):
        pass

    def setComposition(self, composition):
        self.composition = composition

    def editQpts(self, composition, qptDicts):
        for qptDict in qptDicts:
            copyQptToCompositor(composition, qptDict)

    def load_intersection_country_layers(self, names):
        countryLayers = []
        for name in names:
            internationalLayerPath = Path(__file__).parent.parent / 'limites' / f'{name}.shp'
            internacional_layer_fundo = self.loadShapeLayer(
                internationalLayerPath, None, f'{name}_unidades_federativas')
            countryLayers.append(internacional_layer_fundo)
        return countryLayers

    '''
    def get_regioes_info(self, composition, map_extent_feature):      
        self.estados = []
		self.regioes = []	

        # Verifica se no exterior
		if internacional_layer is not None:
			for count, pais_feature in enumerate(internacional_layer.getFeatures()):
				if selectedFeature.geometry().intersects(pais_feature.geometry()):
					self.paises.append(pais_feature['nome'])

		caminho_shp_estado = os.path.join(os.path.dirname(os.path.dirname(__file__)),'limites','2020','Estados_2020.shp')		
		estados_layer_fundo = self.loadShapeLayer(caminho_shp_estado, None, 'estados')


        list_layer_paises = self.load_intersection_country_layers(names)

        map_extent = self.getExtent(map_extent_feature, estados_layer_fundo, internacional_layer_fundo) 
    '''

    def replaceStr(self, original_text, dict_replace):
        for variavel, valor in dict_replace.items():
            original_text = original_text.replace(variavel, str(valor))
        return original_text

    @staticmethod
    def generateElement(parent, tag, attrs={}, text=None):
        element = et.SubElement(parent, tag, attrs)
        if text:
            element.text = text
        return element

    def customEtapa(self, composition, etapas=[]):
        label_tabela_etapas = composition.itemById("label_tabela_etapas")
        if label_tabela_etapas is not None:
            text_label_tabela_etapas = ''

            txt_file = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                    'html_auto', 'etapas_auto.html')
            #filepath = os.path.join(folder, filer)
            file_data = open(txt_file, "r")
            base_html = file_data.read()
            file_data.close()

            rows = []
            for etapa in etapas:
                # Dados Etapa
                row = []
                nome = etapa['nome']
                subetapas = etapa['executantes']
                n_subetapas = len(subetapas)
                for i_subetapa, subetapa in enumerate(subetapas):
                    row.append('<tr>')
                    if i_subetapa == 0:
                        col_nome = self.replaceStr(
                            '<td class = "lef" rowspan="{n_subetapas}">{nome}</td>', {'{n_subetapas}': n_subetapas, '{nome}': nome})
                        row.append(col_nome)
                    responsavel = subetapa['nome']
                    col_responsavel = self.replaceStr(
                        '<td class = "mid" >{responsavel}</td>', {'{responsavel}': responsavel})
                    row.append(col_responsavel)
                    ano = subetapa['ano']
                    col_ano = self.replaceStr('<td class = "rig" >{ano}</td>', {'{ano}': ano})
                    row.append(col_ano)
                    row.append('</tr>')
                # Criando a linha
                rows.append('\n\t'.join(row))

            str_etapas = '\n'.join(rows)

            # Dados ultima edicao
            now = datetime.datetime.now()
            dia = str(now.day)
            meses_pt = {
                1: 'janeiro',
                2: 'fevereiro',
                3: 'março',
                4: 'abril',
                5: 'maio',
                6: 'junho',
                7: 'julho',
                8: 'agosto',
                9: 'setembro',
                10: 'outubro',
                11: 'novembro',
                12: 'dezembro'
            }
            mes = meses_pt[now.month]
            ano = str(now.year)

            dados_data = {
                '{dia}': dia,
                '{mes}': mes,
                '{ano}': ano,
                '{etapas}': str_etapas
            }

            edited = self.replaceStr(base_html, dados_data)
            label_tabela_etapas.setText(edited)

    def customSensores(self, composition, sensores=[]):
        # String to store sensor_txt
        edited = ''
        label_tabela_info_ortoimagem = composition.itemById("label_tabela_info_ortoimagem")

        if label_tabela_info_ortoimagem is not None:
            n_sensores = len(sensores)

            # Get the base html text
            html_file_path = os.path.join(os.path.dirname(
                os.path.dirname(__file__)), 'html_auto', 'sensores_auto_one.html')
            if n_sensores > 1:
                html_file_path = os.path.join(os.path.dirname(os.path.dirname(
                    __file__)), 'html_auto', 'sensores_auto_multiple.html')
            file_data = open(html_file_path, "r")
            base_html = file_data.read()
            file_data.close()

            rows = []
            for sensor in sensores:
                dados_sensor = {
                    '{tipo}': sensor['tipo'],
                    '{plataforma}': sensor['plataforma'],
                    '{nome}': sensor['nome'],
                    '{resolucao}': sensor['resolucao'],
                    '{bandas}': sensor['bandas'],
                    '{nivel_do_produto}': sensor['nivel_produto']
                }
                if n_sensores == 1:
                    # Single Sensor - Done text!
                    edited = self.replaceStr(base_html, dados_sensor)
                elif 1 < n_sensores < 4:
                    base_row_multiple = '<tr >\
                        <td class = "lef" >{tipo}</td>\
                        <td class = "lef" >{plataforma}</td>\
                        <td class = "lef" >{nome}</td>\
                        <td class = "lef" >{resolucao}</td>\
                        <td class = "lef" >{bandas}</td>\
                        <td class = "lef" >{nivel_do_produto}</td>\
                    </tr>'
                    rows.append(self.replaceStr(base_row_multiple, dados_sensor))

            # Multiple sensors
            if 1 < n_sensores < 4:
                str_sensores = '\n'.join(rows)
                edited = self.replaceStr(base_html, {'{sensores}': str_sensores})
            label_tabela_info_ortoimagem.setText(edited)

    def customTecnicalInfo(self, composition, scale, hemisferio, fuso, tipo_produto, tecnicalInfo={}):
        label = composition.itemById("label_tabela_info_carta")
        if label:
            # htmlData = label.text()
            hemisferio = 'Norte' if hemisferio == 'N' else 'Sul'
            falseNorth = '0' if hemisferio == 'Norte' else '+10.000'

            htmlPath = Path(__file__).parent.parent / 'html_auto' / 'technicalInfoBarebone.html'
            htmlData = et.parse(str(htmlPath))
            root = htmlData.getroot()
            firstTable = next(root.iter('table'))
            tr1 = self.generateElement(firstTable, 'tr')
            _ = self.generateElement(tr1, 'td', {'class':'left'}, 'Projeção')
            _ = self.generateElement(tr1, 'td', {'class':'right'}, 'Universal Transversa de Mercator')
            tr2 = self.generateElement(firstTable, 'tr')
            _ = self.generateElement(tr2, 'td', {'class':'left', 'rowspan':'2'}, 'Origem UTM')
            _ = self.generateElement(tr2, 'td', {'class':'right'}, f'Hemisfério {hemisferio}. Equador: {falseNorth} Km')
            label.setText(et.tostring(root, encoding='unicode', method='html'))


    def editHTMLInfoTecCarta(self, composition, scale, hemisferio, fuso, tipo_produto, tecnicalInfo={}):
        '''
        Refreshes the label 'label_tabela_info_carta' with info from json
        '''
        label = composition.itemById("label_tabela_info_carta")
        if label:
            htmlData = label.text()
            htmlPath = Path(__file__).parent.parent / 'html_auto' / 'informacoes_tecnicas_vetores.html'
            with open(htmlPath, 'r') as htmlFile:
                htmlData = htmlFile.read()
            infoDict = {}
            # Techical info from json
            infoDict.update({"{" + k + "}": v for k, v in tecnicalInfo.items() if v != 'dados_terceiros'})
            # Product type
            infoDict.update({"{tipo_produto}": tipo_produto})

            # Get curves info
            dados_curva = curvas[str(scale)]
            for curva, equidistancia_value in dados_curva.items():
                equidistancia_key = "{equidistancia_curva_" + curva + "}"
                infoDict.update({equidistancia_key: str(equidistancia_value)})

            # Update hemisferio e false North
            hemisferio = 'Norte' if hemisferio == 'N' else 'Sul'
            infoDict.update({"{hemisferio}": hemisferio})
            falseNorth = '0' if hemisferio == 'Norte' else '+10.000'
            infoDict.update({"{falseNorth}": falseNorth})

            # Update fuso
            infoDict.update({"{fuso}": fuso})

            # Update meridianoCentral e posicao
            meridianoCentral = -180+(int(fuso)-1)*6 + 3
            infoDict.update({"{meridianoCentral}": str(abs(meridianoCentral))})
            posicao = 'W' if meridianoCentral < 0 else 'E'
            infoDict.update({"{posicao}": posicao})

            # Replace dados data in base html and set text
            label.setText(self.replaceStr(
                htmlData, infoDict))
