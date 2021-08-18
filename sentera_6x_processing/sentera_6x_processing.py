# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Sentera6XProcessing
                                 A QGIS plugin
 This plugin processes mosaics created using Sentera 6X imagery.  Outputs include a 5-band moasic and index layers
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2021-05-11
        git sha              : $Format:%H$
        copyright            : (C) 2021 by Sentera
        email                : gis@sentera.com
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
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *
from qgis.core import *
from qgis.utils import *
from qgis.gui import *
from qgis import processing
import os
from datetime import datetime
from .resources import *
from .sentera_6x_processing_dialog import Sentera6XProcessingDialog
from .sentera_6x_processing_loading_dialog import Sentera6XProcessingDialogLoading
from .sentera_6x_processing_help_dialog import Sentera6XProcessingDialogHelp


class Sentera6XProcessing:
    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'Sentera6XProcessing_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Sentera 6X Post Processing')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('Sentera6XProcessing', message)

    def add_action(self, icon_path, text, callback, enabled_flag=True, add_to_menu=True, add_to_toolbar=True, status_tip=None, whats_this=None, parent=None):

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToRasterMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        qs = QgsSettings()
        if qs.value('UI/UITheme') == 'Night Mapping':
            icon_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "icon_night.png")
        else:
            icon_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "icon_default.png")
        self.add_action(
            icon_path,
            text=self.tr(u'Process 6X Imagery'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginRasterMenu(
                self.tr(u'&Sentera 6X Post Processing'),
                action)
            self.iface.removeToolBarIcon(action)

    def refresh_raster_five_band(self, refresh_code=1):
        # set up layer comboBox
        layers = QgsProject.instance().mapLayers().values()

        # add raster layers to list
        raster_layers = []
        for lay in layers:
            if lay.type() == QgsMapLayer.RasterLayer:
                # only add 5-band mosaics to list
                if lay.bandCount() == 5:
                    raster_layers.append(lay)

        if refresh_code == 1:
            # Clear the contents of the comboBox from previous runs
            self.dlg.five_band_input_box.clear()
            # Populate the comboBox with names the loaded raster layers
            self.dlg.five_band_input_box.addItems([r_layer.name() for r_layer in raster_layers])
        return raster_layers

    def refresh_raster_narrow_bands(self, refresh_code=1):
        # set up layer comboBox
        layers = QgsProject.instance().mapLayers().values()

        # add raster layers to list
        raster_layers = []
        for lay in layers:
            if lay.type() == QgsMapLayer.RasterLayer:
                # only add single band or 2 band mosaics to list
                if lay.bandCount() == 1 or lay.bandCount() == 2:
                    raster_layers.append(lay)

        if refresh_code == 1:
            raster_box_list = [self.dlg.red_band_box,
                               self.dlg.green_band_box,
                               self.dlg.blue_band_box,
                               self.dlg.red_edge_band_box,
                               self.dlg.nir_band_box]
            for box in raster_box_list:
                # Clear the contents of the comboBox from previous runs
                box.clear()
                # Populate the comboBox with names the loaded raster layers
                box.addItems([r_layer.name() for r_layer in raster_layers])
        return raster_layers


    def select_output_folder(self):
        # Get output folder from user
        out_location = QFileDialog.getExistingDirectory(
            self.dlg, "Select Output Directory ")
        self.dlg.outputFolder.setText(out_location)

    def toggle_ndvi_indice(self):
        # check if ndvi/ndre indices are selected, turn on if not, turn off if already on
        if self.dlg.ndviBox.isChecked():
            self.dlg.ndviBox.setChecked(False)
        else:
            self.dlg.ndviBox.setChecked(True)
        if self.dlg.ndreBox.isChecked():
            self.dlg.ndreBox.setChecked(False)
        else:
            self.dlg.ndreBox.setChecked(True)

    def toggle_all_indices(self):
        # check if all indices are on or off
        check_box_list = [self.dlg.ndviBox,
                          self.dlg.ndreBox,
                          self.dlg.gndviBox,
                          self.dlg.ndwiBox,
                          self.dlg.cireBox,
                          self.dlg.cigBox,
                          self.dlg.tcariBox,
                          self.dlg.gliBox]

        for check_box in check_box_list:
            if check_box.isChecked():
                check_box.setChecked(False)
            else:
                check_box.setChecked(True)


    def toggle_index_selection(self):
        # turn on or off indice selection based on index layer check bo
        if self.dlg.generateIndicesButton.isChecked():
            self.dlg.indicesGroup.setEnabled(True)
        else:
            self.dlg.indicesGroup.setEnabled(False)

    def toggle_input_type(self):
        # if 5-band is provided as input, disable it as output
        if self.dlg.inputTab.currentIndex() == 0:
            self.dlg.fiveBandBox.setEnabled(True)
        else:
            self.dlg.fiveBandBox.setEnabled(False)

    def open_help_menu(self):
        self.help_dlg.show()

    def convert_raster_to_float(self, mosaic):
        # convert non-float raster to float.
        print('converting raster')
        mosaic_path = mosaic.dataProvider().dataSourceUri()
        output_path = os.path.normpath(mosaic_path[:-4] + '_f32_temp.tif')
        """
        translate_options = gdal.TranslateOptions(outputType=gdal.GDT_Float32, noData=-10000)
        gdal.Translate(output_path, mosaic_path, options=translate_options)
        """
        translate_params = {
            'COPY_SUBDATASETS': False,
            'DATA_TYPE': 6,
            'EXTRA': '',
            'INPUT': mosaic,
            'NODATA': -10000,
            'OPTIONS': '',
            'TARGET_CRS': None,
            'OUTPUT': output_path
        }
        processing.run('gdal:translate', translate_params)
        return output_path

    def match_extents(self, input_raster, reference_raster, output_dir, band_name):
        # Match raster layer extents
        # Get temp output path
        output_path = os.path.normpath(os.path.join(output_dir, str(band_name + '_aligned_temp.tif')))

        # get reference raster resolution
        x_res = reference_raster.rasterUnitsPerPixelX()
        y_res = reference_raster.rasterUnitsPerPixelY()

        outputs = {}
        # clip input raster by reference raster extent and set resolution of reference raster
        clip_params = {
            'DATA_TYPE': 0,
            'EXTRA': '-r average -tr {} {}'.format(x_res, y_res),
            'INPUT': input_raster,
            'NODATA': None,
            'OPTIONS': '',
            'PROJWIN': reference_raster,
            'OUTPUT': output_path
        }
        outputs['ClipRasterByExtent'] = processing.run('gdal:cliprasterbyextent', clip_params)

        return QgsRasterLayer(output_path, str(band_name + 'aligned'))

    def extract_band(self, raster_layer, band_number, band_name, output_dir):
        # Create single band narrow channel mosaic from 2-channel mosaic(produced by pix4d)

        temp_out_path = os.path.join(output_dir, os.path.normpath(band_name + '_temp.tif'))
        input_path = raster_layer.dataProvider().dataSourceUri()

        # extract reflectance values from band 1
        '''
        Calc("A*(A>0) + -10000*(A<=0)", A=input_path, A_band=band_number, outfile=temp_out_path, NoDataValue=-10000)
        '''
        one_band_params = {
            'BAND_A': band_number,
            'EXTRA': '',
            'FORMULA': "A*(A>0) + -10000*(A<=0)",
            'INPUT_A': input_path,
            'NO_DATA': -10000,
            'OPTIONS': '',
            'RTYPE': 5,
            'OUTPUT': temp_out_path
        }
        processing.run('gdal:rastercalculator', one_band_params)

        band_one_raster = QgsRasterLayer(temp_out_path, raster_layer.name())

        return band_one_raster

    def create_five_band(self, data_dictionary, output_directory, output_base):
        # Create five band mosaic
        output_path = os.path.join(output_directory, str(output_base + '_6X_5_band_mosaic.tif'))

        '''
        # Run gdal_merge using separate tag and set nodata as -10000
        gm.main(['', '-separate', '-n', '-10000', '-a_nodata', '-10000', '-o', output_path,
                 data_dictionary['RED_band'].dataProvider().dataSourceUri(),
                 data_dictionary['GREEN_band'].dataProvider().dataSourceUri(),
                 data_dictionary['BLUE_band'].dataProvider().dataSourceUri(),
                 data_dictionary['RED_EDGE_band'].dataProvider().dataSourceUri(),
                 data_dictionary['NIR_band'].dataProvider().dataSourceUri()
                 ])
        '''

        alg_params = {
            'DATA_TYPE': 5,
            'EXTRA': '',
            'INPUT': [data_dictionary['RED_band'].dataProvider().dataSourceUri(),
                        data_dictionary['GREEN_band'].dataProvider().dataSourceUri(),
                        data_dictionary['BLUE_band'].dataProvider().dataSourceUri(),
                        data_dictionary['RED_EDGE_band'].dataProvider().dataSourceUri(),
                        data_dictionary['NIR_band'].dataProvider().dataSourceUri()],
            'NODATA_INPUT': None,
            'NODATA_OUTPUT': None,
            'OPTIONS': '',
            'PCT': False,
            'SEPARATE': True,
            'OUTPUT': output_path
        }
        processing.run('gdal:merge', alg_params)

        five_band_layer = QgsRasterLayer(output_path, str(output_base + '_6X_5_band_mosaic'))
        # set 5-band layer styling to correctly display mosaic and correctly extract RGB
        five_band_layer.setContrastEnhancement(QgsContrastEnhancement.StretchToMinimumMaximum, QgsRasterMinMaxOrigin.MinMax)
        if self.dlg.loadBox.isChecked():
            QgsProject.instance().addMapLayer(five_band_layer)

        return five_band_layer

    def generate_indices(self, data_dictionary, indice_list, output_dir, output_base):


        if '5_BAND_LAYER' in data_dictionary:
            # if 5-band mosaic exists, use to generate indices
            red = data_dictionary['5_BAND_LAYER'].dataProvider().dataSourceUri()
            green = data_dictionary['5_BAND_LAYER'].dataProvider().dataSourceUri()
            blue = data_dictionary['5_BAND_LAYER'].dataProvider().dataSourceUri()
            red_edge = data_dictionary['5_BAND_LAYER'].dataProvider().dataSourceUri()
            nir = data_dictionary['5_BAND_LAYER'].dataProvider().dataSourceUri()
            red_band = 1
            green_band = 2
            blue_band = 3
            red_edge_band = 4
            nir_band = 5
        else:
            # if no 5-band mosaic was generated, create indices using single bands
            red = data_dictionary['RED_band'].dataProvider().dataSourceUri()
            green = data_dictionary['GREEN_band'].dataProvider().dataSourceUri()
            blue = data_dictionary['BLUE_band'].dataProvider().dataSourceUri()
            red_edge = data_dictionary['RED_EDGE_band'].dataProvider().dataSourceUri()
            nir = data_dictionary['NIR_band'].dataProvider().dataSourceUri()
            red_band = 1
            green_band = 1
            blue_band = 1
            red_edge_band = 1
            nir_band = 1

        if 'NDVI' in indice_list:
            # NDVI EQUATION: (NIR - RED)/(NIR + RED)
            ndvi_output_path = os.path.join(output_dir, str(output_base + '_ndvi_index.tif'))

            '''
            Calc("(E - A)/(E + A)", A=red, E=nir, A_band=red_band, E_band=nir_band, outfile=ndvi_output_path,
                 NoDataValue=-10000)
            '''
            ndvi_params = {
                'BAND_A': red_band,
                'BAND_E': nir_band,
                'EXTRA': '',
                'FORMULA': "(E - A)/(E + A)",
                'INPUT_A': red,
                'INPUT_E': nir,
                'NO_DATA': -10000,
                'OPTIONS': '',
                'RTYPE': 5,
                'OUTPUT': ndvi_output_path
            }
            processing.run('gdal:rastercalculator', ndvi_params)

            if self.dlg.loadBox.isChecked():
                ndvi_layer = QgsRasterLayer(ndvi_output_path, str(output_base + '_ndvi_index'))
                QgsProject.instance().addMapLayer(ndvi_layer)

        if 'NDRE' in indice_list:
            # NDRE EQUATION: (NIR - RED_EDGE)/(NIR + RED_EDGE)
            ndre_output_path = os.path.join(output_dir, str(output_base + '_ndre_index.tif'))

            '''
            Calc("(E - D)/(E + D)", D=red_edge, E=nir, D_band=red_edge_band, E_band=nir_band, outfile=ndre_output_path,
                 NoDataValue=-10000)
            '''

            ndre_params = {
                'BAND_A': red_edge_band,
                'BAND_D': red_edge_band,
                'BAND_E': nir_band,
                'EXTRA': '',
                'FORMULA': "(E - D)/(E + D)",
                'INPUT_A': red_edge,
                'INPUT_D': red_edge,
                'INPUT_E': nir,
                'NO_DATA': -10000,
                'OPTIONS': '',
                'RTYPE': 5,
                'OUTPUT': ndre_output_path
            }
            processing.run('gdal:rastercalculator', ndre_params)

            if self.dlg.loadBox.isChecked():
                ndre_layer = QgsRasterLayer(ndre_output_path, str(output_base + '_ndre_index'))
                QgsProject.instance().addMapLayer(ndre_layer)

        if 'GNDVI' in indice_list:
            # GNDVI EQUATION: (NIR - GREEN)/(NIR + GREEN)
            gndvi_output_path = os.path.join(output_dir, str(output_base + '_gndvi_index.tif'))

            '''
            Calc("(E - B)/(E + B)", B=green, E=nir, B_band=green_band, E_band=nir_band, outfile=gndvi_output_path,
                 NoDataValue=-10000)
            '''

            gndvi_params = {
                'BAND_A': green_band,
                'BAND_B': green_band,
                'BAND_E': nir_band,
                'EXTRA': '',
                'FORMULA': "(E - B)/(E + B)",
                'INPUT_A': green,
                'INPUT_B': green,
                'INPUT_E': nir,
                'NO_DATA': -10000,
                'OPTIONS': '',
                'RTYPE': 5,
                'OUTPUT': gndvi_output_path
            }
            processing.run('gdal:rastercalculator', gndvi_params)

            if self.dlg.loadBox.isChecked():
                gndvi_layer = QgsRasterLayer(gndvi_output_path, str(output_base + '_gndvi_index'))
                QgsProject.instance().addMapLayer(gndvi_layer)

        if 'NDWI' in indice_list:
            # NDWI EQUATION: (GREEN - NIR)/(GREEN + NIR)
            ndwi_output_path = os.path.join(output_dir, str(output_base + '_ndwi_index.tif'))

            '''
            Calc("(B - E)/(B + E)", B=green, E=nir, B_band=green_band, E_band=nir_band, outfile=ndwi_output_path,
                 NoDataValue=-10000)
            '''

            ndwi_params = {
                'BAND_A': green_band,
                'BAND_B': green_band,
                'BAND_E': nir_band,
                'EXTRA': '',
                'FORMULA': "(B - E)/(B + E)",
                'INPUT_A': green,
                'INPUT_B': green,
                'INPUT_E': nir,
                'NO_DATA': -10000,
                'OPTIONS': '',
                'RTYPE': 5,
                'OUTPUT': ndwi_output_path
            }
            processing.run('gdal:rastercalculator', ndwi_params)

            if self.dlg.loadBox.isChecked():
                ndwi_layer = QgsRasterLayer(ndwi_output_path, str(output_base + '_ndwi_index'))
                QgsProject.instance().addMapLayer(ndwi_layer)

        if 'CIRE' in indice_list:
            # CIRE EQUATION: (NIR - RED_EDGE) - 1
            cire_output_path = os.path.join(output_dir, str(output_base + '_cire_index.tif'))

            '''
            Calc("(E - D) - 1", D=red_edge, E=nir, D_band=red_edge_band, E_band=nir_band, outfile=cire_output_path,
                 NoDataValue=-10000)
            '''

            cire_params = {
                'BAND_A': red_edge_band,
                'BAND_D': red_edge_band,
                'BAND_E': nir_band,
                'EXTRA': '',
                'FORMULA': "(E - D) - 1",
                'INPUT_A': red_edge,
                'INPUT_D': red_edge,
                'INPUT_E': nir,
                'NO_DATA': -10000,
                'OPTIONS': '',
                'RTYPE': 5,
                'OUTPUT': cire_output_path
            }
            processing.run('gdal:rastercalculator', cire_params)

            if self.dlg.loadBox.isChecked():
                cire_layer = QgsRasterLayer(cire_output_path, str(output_base + '_cire_index'))
                QgsProject.instance().addMapLayer(cire_layer)

        if 'CIG' in indice_list:
            # CIG EQUATION: (NIR - GREEN) - 1
            cig_output_path = os.path.join(output_dir, str(output_base + '_cig_index.tif'))

            '''
            Calc("(E - B) - 1", B=green, E=nir, B_band=green_band, E_band=nir_band, outfile=cig_output_path,
                 NoDataValue=-10000)
            '''

            cig_params = {
                'BAND_A': green_band,
                'BAND_B': green_band,
                'BAND_E': nir_band,
                'EXTRA': '',
                'FORMULA': "(E - B) - 1",
                'INPUT_A': green,
                'INPUT_B': green,
                'INPUT_E': nir,
                'NO_DATA': -10000,
                'OPTIONS': '',
                'RTYPE': 5,
                'OUTPUT': cig_output_path
            }
            processing.run('gdal:rastercalculator', cig_params)

            if self.dlg.loadBox.isChecked():
                cig_layer = QgsRasterLayer(cig_output_path, str(output_base + '_cig_index'))
                QgsProject.instance().addMapLayer(cig_layer)

        if 'TCARI OSAVI' in indice_list:
            #  T-O Equation: (3 * ((RED_EDGE – RED)–0.2*(RED_EDGE – GREEN)*(RED_EDGE / RED)) / (1.16 * (NIR – RED)/(NIR + RED + .16)))
            tcari_output_path = os.path.join(output_dir, str(output_base + '_tcari_osavi_index.tif'))

            '''
            Calc("(3*((D-A)-0.2*(D-B)*(D/A))/(1.16*(E-A)/(E+A+0.16)))",
                 A=red, B=green, D=red_edge, E=nir,
                 A_band=red_band, B_band=green_band, D_band=red_edge_band, E_band=nir_band,
                 outfile=tcari_output_path, NoDataValue=-10000)
            '''

            t_o_params = {
                'BAND_A': red_band,
                'BAND_B': green_band,
                'BAND_D': red_edge_band,
                'BAND_E': nir_band,
                'EXTRA': '',
                'FORMULA': "(3*((D-A)-0.2*(D-B)*(D/A))/(1.16*(E-A)/(E+A+0.16)))",
                'INPUT_A': red,
                'INPUT_B': green,
                'INPUT_D': red_edge,
                'INPUT_E': nir,
                'NO_DATA': -10000,
                'OPTIONS': '',
                'RTYPE': 5,
                'OUTPUT': tcari_output_path
            }
            processing.run('gdal:rastercalculator', t_o_params)

            if self.dlg.loadBox.isChecked():
                tcari_layer = QgsRasterLayer(tcari_output_path, str(output_base + '_tcari_osavi_index'))
                QgsProject.instance().addMapLayer(tcari_layer)

        if 'GLI' in indice_list:
            # GLI EQUATION: (2*GREEN - RED - BLUE)/(2*GREEN + RED + BLUE)
            gli_output_path = os.path.join(output_dir, str(output_base + '_gli_index.tif'))

            '''
            Calc("((2*B)-A-C)/((2*B)+A+C)", A=red, B=green, C=blue, A_band=red_band, B_band=green_band,
                 C_band=blue_band,
                 outfile=gli_output_path, NoDataValue=-10000)
            '''

            gli_params = {
                'BAND_A': red_band,
                'BAND_B': green_band,
                'BAND_C': blue_band,
                'EXTRA': '',
                'FORMULA': "((2*B)-A-C)/((2*B)+A+C)",
                'INPUT_A': red,
                'INPUT_B': green,
                'INPUT_C': blue,
                'NO_DATA': -10000,
                'OPTIONS': '',
                'RTYPE': 5,
                'OUTPUT': gli_output_path
            }
            processing.run('gdal:rastercalculator', gli_params)

            if self.dlg.loadBox.isChecked():
                gli_layer = QgsRasterLayer(gli_output_path, str(output_base + '_gli_index'))
                QgsProject.instance().addMapLayer(gli_layer)

        # clear data dictionary so temp files can be deleted if necessary
        data_dictionary = None


    def run(self):
        """Run method that performs all the real work"""

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            self.first_start = False
            self.dlg = Sentera6XProcessingDialog()
            self.load_dlg = Sentera6XProcessingDialogLoading()
            self.help_dlg = Sentera6XProcessingDialogHelp()
            self.dlg.outputButton.clicked.connect(self.select_output_folder)
            self.dlg.selectAllButton.clicked.connect(self.toggle_all_indices)
            self.dlg.selectNDButton.clicked.connect(self.toggle_ndvi_indice)
            self.dlg.generateIndicesButton.clicked.connect(self.toggle_index_selection)
            self.dlg.inputTab.currentChanged.connect(self.toggle_input_type)
            self.dlg.helpButton.clicked.connect(self.open_help_menu)


        self.refresh_raster_narrow_bands(1)
        self.refresh_raster_five_band(1)
        self.toggle_index_selection()
        self.toggle_input_type()

        # Run the dialog event loop
        self.dlg.show()
        result = self.dlg.exec_()

        # See if OK was pressed
        if result:
            self.load_dlg.show()
            self.load_dlg.loadText.insertPlainText('Generating Outputs\n')
            self.help_dlg.close()
            # get processing start time
            start_time = datetime.now()
            print('6x processing start::{}'.format(start_time))
            # get output directory
            output_dir = self.dlg.outputFolder.text()
            # check if output directory exists
            if not os.path.isdir(output_dir):
                os.mkdir(output_dir)
            output_base = self.dlg.outputBase.text()

            band_name_list = ['RED', 'GREEN', 'BLUE', 'RED_EDGE', 'NIR']
            six_x_data_dict = {}


            if self.dlg.inputTab.currentIndex() == 0:
                # store raster layers in dictionary and add input band names to band name list
                # Get single band layers
                raster_layers = self.refresh_raster_narrow_bands(0)

                red_band_layer_index = self.dlg.red_band_box.currentIndex()
                six_x_data_dict['RED'] = raster_layers[red_band_layer_index]

                green_band_layer_index = self.dlg.green_band_box.currentIndex()
                six_x_data_dict['GREEN'] = raster_layers[green_band_layer_index]

                blue_band_layer_index = self.dlg.blue_band_box.currentIndex()
                six_x_data_dict['BLUE'] = raster_layers[blue_band_layer_index]

                red_edge_band_layer_index = self.dlg.red_edge_band_box.currentIndex()
                six_x_data_dict['RED_EDGE'] = raster_layers[red_edge_band_layer_index]

                nir_band_layer_index = self.dlg.nir_band_box.currentIndex()
                six_x_data_dict['NIR'] = raster_layers[nir_band_layer_index]

                # Check single band input type, if input is 2-band corrected imagery mosaic, convert to single band
                # for 5-band mosaic generation or index generation
                for b in band_name_list:
                    if six_x_data_dict[b].bandCount() == 2:
                        six_x_data_dict[str(b + '_band')] = self.extract_band(six_x_data_dict[b], 1, b,
                                                                              output_dir)
                    elif six_x_data_dict[b].bandCount() == 1:
                        six_x_data_dict[str(b + '_band')] = six_x_data_dict[b]
                if self.dlg.fiveBandBox.isChecked():
                    six_x_data_dict['5_BAND_LAYER'] = self.create_five_band(six_x_data_dict, output_dir,
                                                                            output_base)

            elif self.dlg.inputTab.currentIndex() == 1:
                # if 5-band mosaic provided, create band name list
                raster_layers = self.refresh_raster_five_band(0)
                five_band_layer_index = self.dlg.five_band_input_box.currentIndex()
                six_x_data_dict['5_BAND_LAYER'] = raster_layers[five_band_layer_index]

                # check 5-band mosaic data type, if type is not float32, convert to float

                """
                five_band_type_test = gdal.Open(six_x_data_dict['5_BAND_LAYER'].dataProvider().dataSourceUri())
                band_1 = five_band_type_test.GetRasterBand(1)
                print(gdal.GetDataTypeName(band_1.DataType))
                """

                if six_x_data_dict['5_BAND_LAYER'].dataProvider().dataType(1) != 6:
                    six_x_data_dict['5_BAND_LAYER'] = QgsRasterLayer(self.convert_raster_to_float(
                        six_x_data_dict['5_BAND_LAYER']), 'five_band_float')

                # set 5-band layer style
                five_band_layer = six_x_data_dict['5_BAND_LAYER']
                five_band_layer.setContrastEnhancement(QgsContrastEnhancement.StretchToMinimumMaximum,
                                                       QgsRasterMinMaxOrigin.MinMax)
                five_band_layer.triggerRepaint()

            if self.dlg.generateIndicesButton.isChecked():
                # create list of selected indices
                indice_list = []
                required_band_list = []
                if self.dlg.ndviBox.isChecked():
                    indice_list.append('NDVI')
                    required_band_list.append('RED')
                    required_band_list.append('NIR')
                if self.dlg.ndreBox.isChecked():
                    indice_list.append('NDRE')
                    required_band_list.append('RED_EDGE')
                    required_band_list.append('NIR')
                if self.dlg.gndviBox.isChecked():
                    indice_list.append('GNDVI')
                    required_band_list.append('GREEN')
                    required_band_list.append('NIR')
                if self.dlg.ndwiBox.isChecked():
                    indice_list.append('NDWI')
                    required_band_list.append('GREEN')
                    required_band_list.append('NIR')
                if self.dlg.cireBox.isChecked():
                    indice_list.append('CIRE')
                    required_band_list.append('RED_EDGE')
                    required_band_list.append('NIR')
                if self.dlg.cigBox.isChecked():
                    indice_list.append('CIG')
                    required_band_list.append('GREEN')
                    required_band_list.append('NIR')
                if self.dlg.tcariBox.isChecked():
                    indice_list.append('TCARI OSAVI')
                    required_band_list.append('RED')
                    required_band_list.append('NIR')
                    required_band_list.append('RED_EDGE')
                    required_band_list.append('GREEN')
                if self.dlg.gliBox.isChecked():
                    indice_list.append('GLI')
                    required_band_list.append('RED')
                    required_band_list.append('GREEN')
                    required_band_list.append('BLUE')

                if indice_list is not None:
                    # Check if single band layers are the same size
                    print('Checking single band size')
                    width_list = []
                    height_list = []
                    if '5_BAND_LAYER' in six_x_data_dict:
                        # if 5-band mosaic exists, use 5-band for index creation
                        pass
                    else:
                        required_band_set = set(required_band_list)
                        for ban in required_band_set:
                            width_list.append(six_x_data_dict[str(ban + '_band')].width())
                            height_list.append(six_x_data_dict[str(ban + '_band')].height())

                        width_set = set(width_list)
                        height_set = set(height_list)
                        if len(height_set) > 1 or len(width_set) > 1:
                            # if there are more than one size for height or width, re-size layers
                            print('raster sizes are different, re-aligning')
                            for ba in required_band_set:
                                six_x_data_dict[str(ba + '_band')] = self.match_extents(
                                    six_x_data_dict[str(ba + '_band')],
                                    six_x_data_dict[str(required_band_set[0] + '_band')],
                                    output_dir, ba)

                    # generate selected indices
                    self.generate_indices(six_x_data_dict, indice_list, output_dir, output_base)



            if self.dlg.rgbBox.isChecked():
                print('generating rgb layer')
                # get info from 5-band mosaic and export rendering as 3 band byte mosaic
                five_band_mosaic = six_x_data_dict['5_BAND_LAYER']
                extent = five_band_mosaic.extent()
                width, height = five_band_mosaic.width(), five_band_mosaic.height()
                renderer = five_band_mosaic.renderer()
                provider = five_band_mosaic.dataProvider()
                pipe = QgsRasterPipe()
                pipe.set(provider.clone())
                pipe.set(renderer.clone())
                rgb_path = os.path.join(output_dir, output_base) + '_6X_RGB_mosaic.tif'
                file_writer = QgsRasterFileWriter(rgb_path)
                file_writer.writeRaster(pipe,
                                        width,
                                        height,
                                        extent,
                                        five_band_mosaic.crs())
                if self.dlg.loadBox.isChecked():
                    rgb_layer = QgsRasterLayer(rgb_path, os.path.split(rgb_path)[1][:-4])
                    QgsProject.instance().addMapLayer(rgb_layer)

            # delete temporary files
            six_x_data_dict = None

            self.load_dlg.loadText.insertPlainText('Processing Complete\nOutputs saved to: {}'.format(output_dir))


            file_list = [f for f in os.listdir(output_dir) if os.path.isfile(os.path.join(output_dir, f))]
            for f in file_list:
                if f.endswith('temp.tif'):
                    try:
                        os.remove(os.path.join(output_dir, f))
                    except:
                        pass

            # save processing end time and print the elasped time
            end_time = datetime.now()
            print('Processing Compelte::{}'.format(end_time))
            print('Time Elapsed: {}'.format(end_time - start_time))






