######################
#                                    
#  Byron C. Wallace                   
#  Tufts Medical Center              
#  OpenMeta[analyst]                 
#                                     
#  This is the code for the ui dialog 
#  that handles the method selection  
#  and algorithm specifications       
#                                     
########################


from PyQt4 import QtCore, QtGui, Qt
from PyQt4.Qt import *
import pdb
import sip

import ui_ma_specs
import meta_py_r


class MA_Specs(QDialog, ui_ma_specs.Ui_Dialog):

    def __init__(self, model, parent=None):
        super(MA_Specs, self).__init__(parent)
        self.setupUi(self)
        self.model = model

        QObject.connect(self.buttonBox, SIGNAL("accepted()"), self.run_ma)
        QObject.connect(self.buttonBox, SIGNAL("rejected()"), self.cancel)
        QObject.connect(self.method_cbo_box, SIGNAL("currentIndexChanged(QString)"),
                                             self.method_changed)

        self.data_type = self.model.get_current_outcome_type()
        #pyqtRemoveInputHook()
        #pdb.set_trace()
        print "data type: %s" % self.data_type
        self.current_widgets = []
        self.current_method = None
        self.current_params = None
        self.current_defaults = None
        self.var_order = None
        self.current_param_vals = {}
        self.populate_cbo_box()
        # now we set up a UI for the parameters
        # required for the current method
        #self.ui_for_params()

    def cancel(self):
        print "(cancel)"
        self.reject()

    def run_ma(self):
        result = None
        # dispatch on type; build an R object, then run the analysis
        if self.data_type == "binary":
            # note that this call creates a tmp object in R called
            # tmp_obj (though you can pass in whatever var name
            # you'd like)
            meta_py_r.ma_dataset_to_simple_binary_robj(self.model)
            result = meta_py_r.run_binary_ma(self.current_method, self.current_param_vals)
        elif self.data_type == "continuous":
            meta_py_r.ma_dataset_to_simple_continuous_robj(self.model)
            result = meta_py_r.run_continuous_ma(self.current_method, self.current_param_vals)
        self.parent().analysis(result)
        self.accept()

    def method_changed(self):
        self.clear_param_ui()
        self.current_widgets= []
        self.current_method = self.method_cbo_box.currentText()
        self.setup_params()
        self.parameter_grp_box.setTitle(self.current_method)
        self.ui_for_params()

    def populate_cbo_box(self):
        # we first build an R object with the current data. this is to pass off         
        # to the R side to check the feasibility of the methods over the current data.
        # i.e., we do not display methods that cannot be performed over the 
        # current data.
        tmp_obj_name = "tmp_obj" 
        if self.data_type == "binary":
            meta_py_r.ma_dataset_to_simple_binary_robj(self.model, var_name=tmp_obj_name)
        elif self.data_type == "continuous":
            meta_py_r.ma_dataset_to_simple_continuous_robj(self.model, var_name=tmp_obj_name)
            
        available_methods = meta_py_r.get_available_methods(for_data_type=self.data_type, data_obj_name=tmp_obj_name)
        print "\n\navailable %s methods: %s" % (self.data_type, ", ".join(available_methods))
        for method in available_methods:
            self.method_cbo_box.addItem(method)
        self.current_method = self.method_cbo_box.currentText()
        self.setup_params()
        self.parameter_grp_box.setTitle(self.current_method)


    def clear_param_ui(self):
        for widget in self.current_widgets:
            widget.deleteLater()
            widget = None


    def ui_for_params(self):
        if self.parameter_grp_box.layout() is None:
           layout = QGridLayout()
           self.parameter_grp_box.setLayout(layout)

        cur_grid_row = 0
        
        if self.var_order is not None:
            for var_name in self.var_order:
                val = self.current_params[var_name]
                self.add_param(self.parameter_grp_box.layout(), cur_grid_row, var_name, val)
                cur_grid_row+=1
        else:
            # no ordering was provided; let's try and do something
            # sane with respect to the order in which parameters
            # are displayed.
            #
            # we want to add the parameters in groups, for example,
            # we add combo boxes (which will be lists of values) together,
            # followed by numerical inputs. thus we create an ordered list
            # of functions to check if the argument is the corresponding
            # type (float, list); if it is, we add it otherwise we pass. this isn't
            # the most efficient way to do things, but the number of parameters
            # is going to be relatively tiny anyway
            ordered_types = [lambda x: isinstance(x, list), \
                                        lambda x: isinstance(x, str) and x.lower()=="float"]
    
            for is_right_type in ordered_types:
                for key, val in self.current_params.items():
                    if is_right_type(val):
                        self.add_param(self.parameter_grp_box.layout(), cur_grid_row, key, val)
                        cur_grid_row+=1

    def add_param(self, layout, cur_grid_row, name, value):
        print "adding param. name: %s, value: %s" % (name, value)
        if isinstance(value, list):
            # then it's an enumeration of values
            self.add_enum(layout, cur_grid_row, name, value)
        elif value.lower() == "float":
            self.add_float_box(layout, cur_grid_row, name)
        else:
            print "uknown type! throwing up. bleccch."
            print "name:%s. value: %s" % (name, value)
            # throw exception here

    def add_enum(self, layout, cur_grid_row, name, values):
        '''
        Adds an enumeration to the UI, with the name and possible
        values as specified per the parameters.
        '''
        self.add_label(layout, cur_grid_row, name)
        cbo_box = QComboBox()
        for value in values:
            cbo_box.addItem(value)

        if self.current_defaults.has_key(name):
            cbo_box.setCurrentIndex(cbo_box.findText(self.current_defaults[name]))
            self.current_param_vals[name] = self.current_defaults[name]

        QObject.connect(cbo_box, QtCore.SIGNAL("currentIndexChanged(QString)"),
                                 self.set_param_f(name))

        self.current_widgets.append(cbo_box)
        layout.addWidget(cbo_box, cur_grid_row, 1)

    def add_float_box(self, layout, cur_grid_row, name):
        self.add_label(layout, cur_grid_row, name)
        # now add the float input line edit
        finput = QLineEdit()

        # if a default value has been specified, use it
        if self.current_defaults.has_key(name):
            finput.setText(str(self.current_defaults[name]))
            self.current_param_vals[name] = self.current_defaults[name]

        finput.setMaximumWidth(50)
        QObject.connect(finput, QtCore.SIGNAL("textChanged(QString)"),
                                 self.set_param_f(name, to_type=float))
        self.current_widgets.append(finput)
        layout.addWidget(finput, cur_grid_row, 1)

    def set_param_f(self, name, to_type=str):
        '''
        Returns a function f(x) such that f(x) will set the key
        name in the parameters dictionary to the value x.
        '''
        def set_param(x):
            self.current_param_vals[name] = to_type(x)
            print self.current_param_vals

        return set_param

    def add_label(self, layout, cur_grid_row, name):
        lbl = QLabel(name, self.parameter_grp_box)
        self.current_widgets.append(lbl)
        layout.addWidget(lbl, cur_grid_row, 0)

    def setup_params(self):
        self.current_params, self.current_defaults, self.var_order = meta_py_r.get_params(self.current_method)
        print self.current_defaults
