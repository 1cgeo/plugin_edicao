import datetime
import math
import os

from dateutil.relativedelta import relativedelta
from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject

from .angles.auxiliar.auxiliar import Auxiliar
from .angles.geomag.geomag import GeoMag


class HandleAngles:
    def __init__(self, iface):
        self.iface = iface
        self.auxiliar = Auxiliar(iface)

    def setComposition(self, composition):
        self.composition = composition

    def setCustomMode(self):
        self.customMode = True

    def make(self, composition, selected_feature):
        point = None

        geom = selected_feature.geometry()
        convexhull = geom.convexHull()
        # point = convexhull.centroid().asPoint()
        point = geom.centroid().asPoint()

        wgsPoint = self.getWGSPoint(point)

        convergencia = self.auxiliar.calculateConvergence(wgsPoint)
        file = os.path.join(os.path.dirname(__file__), 'angles', 'geomag', 'WMM.cof')

        gm = GeoMag(file)
        height = 0
        time = datetime.date(year=2021, month=1, day=1)
        decl_today = gm.GeoMag(wgsPoint.y(), wgsPoint.x(), height, time=time)
        year_ago = time + relativedelta(years=1)
        decl_yearago = gm.GeoMag(wgsPoint.y(), wgsPoint.x(), height, year_ago)
        yearlydelta_declination = decl_yearago.dec-decl_today.dec
        #decl = geomag.declination(wgsPoint.y(), wgsPoint.x())

        # self.setConvergencia(convergencia)
        # self.setDeclinacao(decl_today.dec)
        self.replaceData(composition, convergencia, decl_today.dec, yearlydelta_declination)

    def setConvergencia(self, conv):
        convergencia = self.generateDMS(conv)

    def setDeclinacao(self, decl):
        declinacao = self.generateDMS(decl)

    def getWGSPoint(self, pt):
        crsSrc = self.iface.mapCanvas().mapSettings().destinationCrs()
        crsDest = QgsCoordinateReferenceSystem(4326, QgsCoordinateReferenceSystem.EpsgCrsId)

        coordinateTransformer = QgsCoordinateTransform(crsSrc, crsDest, QgsProject.instance())
        wgsPt = coordinateTransformer.transform(pt)
        return wgsPt

    def generateConvText(self, ang):
        xg = math.modf(ang)[1]
        #xg = format( int(math.modf( ang )[1]), '2.0f' )
        sign = -1 if ang < 0 else 1
        xm = format(sign * math.modf(math.modf(ang)[0] * 60)[1], '.0f')
        xs = format(sign * math.modf(math.modf(ang)[0] * 60)[0] * 60, '.0f')
        # gms = ('%02d' % ((xg)))	  + u"° " + ('%02d' % (int(xm))) + "' " + ('%02d' % (int(xs))) + '"'
        gms = str(xg) + u"° " + str(xm) + "' " + str(xs) + '"'
        gms = gms.encode('utf8')
        return gms.decode('utf8')

    def generateDecText(self, ang):
        xg = format(math.modf(ang)[1], '.0f')
        sign = -1 if ang < 0 else 1
        xm = format(sign * math.modf(math.modf(ang)[0] * 60)[1], '.0f')
        xs = format(sign * math.modf(math.modf(ang)[0] * 60)[0] * 60, '.0f')
        gms = str(xg) + u"° " + str(xm) + "'"
        gms = gms.encode('utf8')
        return gms.decode('utf8')

    def generateDMS(self, ang):
        xg = format(math.modf(ang)[1], '.0f')
        sign = -1 if ang < 0 else 1
        xm = format(sign * math.modf(math.modf(ang)[0] * 60)[1], '.0f')
        xs = format(sign * math.modf(math.modf(ang)[0] * 60)[0] * 60, '.0f')
        # xs = format( sign * math.modf( math.modf( ang )[0] * 60 )[0] * 60, '.3f' )
        gms = str(xg) + u"° " + str(xm).zfill(2) + "' " + str(xs).zfill(2) + '"'
        gms = gms.encode('utf8')
        return gms.decode('utf8')

    def generateDeltaSTR(self, ang):
        xg = format(math.modf(ang)[1], '.0f')
        sign = -1 if ang < 0 else 1
        inte = sign * math.modf(math.modf(ang)[0] * 60)[1]
        deci = sign * math.modf(math.modf(ang)[0] * 60)[0]
        xm_edited = sign*(round((inte+deci), 1))
        gms = (str(xm_edited) + "' ").replace('.', ',')
        gms = gms.encode('utf8')
        return gms.decode('utf8')

    def replaceData(self, composition, convergencia, declinacao, yearlydelta_declination):
        # Yearly declination delta
        label_yearlyDeclinationDelta = composition.itemById('label_yearlyDeclinationDelta')
        if label_yearlyDeclinationDelta is not None:
            base_text = "A DECLINAÇÃO MAGNÉTICA\
						CRESCE {} ANUALMENTE"
            label_yearlyDeclinationDelta_text = base_text.format(
                self.generateDeltaSTR(yearlydelta_declination))
            label_yearlyDeclinationDelta.setText(label_yearlyDeclinationDelta_text)
            label_yearlyDeclinationDelta.refresh()

        visible_ids = "Dir.MCaoSuldoEquadoreEsq.MCaoNortedoEquador"
        invisible_ids = 'Esq.MCaoSuldoEquadoreDirMCaoNortedoEquador'
        if convergencia > 0:
            visible_ids = 'Esq.MCaoSuldoEquadoreDirMCaoNortedoEquador'
            invisible_ids = 'Dir.MCaoSuldoEquadoreEsq.MCaoNortedoEquador'

        # Setting declinacao
        declination_id = visible_ids + '-dm_textLabel'
        label_declination = composition.itemById(declination_id)
        if label_declination is not None:
            label_declination.setText(self.generateDecText(declinacao))
            label_declination.refresh()

        # Setting convergencia
        convergence_id = visible_ids + '-cm_textLabel'
        label_convergence = composition.itemById(convergence_id)
        if label_convergence is not None:
            label_convergence.setText(self.generateDMS(convergencia))
            label_convergence.refresh()

        composition_list = (composition.items())
        for compositionItem in composition_list:
            check_label = (compositionItem).__class__.__name__ == 'QgsLayoutItemLabel'
            check_shape = (compositionItem).__class__.__name__ == 'QgsLayoutItemPolygon'
            check_polyline = (compositionItem).__class__.__name__ == 'QgsLayoutItemPolyline'
            check_picture = (compositionItem).__class__.__name__ == 'QgsLayoutItemPicture'
            check_all = check_label or check_shape or check_polyline or check_picture
            if check_all:
                item_id = compositionItem.id()
                if visible_ids in item_id:
                    compositionItem.setVisibility(True)
                elif invisible_ids in item_id:
                    compositionItem.setVisibility(False)
                else:
                    pass
