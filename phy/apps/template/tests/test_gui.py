# -*- coding: utf-8 -*-

"""Testing the Template model."""

#------------------------------------------------------------------------------
# Imports
#------------------------------------------------------------------------------

import logging

from phylib.utils._misc import _read_python
from phylib.utils.testing import captured_output
from phylib.utils import connect, emit
from phy.cluster.views import WaveformView, TraceView, ProbeView, RasterView, TemplateView
from phy.gui.widgets import Barrier
from phy.plot.tests import key_press, mouse_click
from ..gui import TemplateController, template_describe, AmplitudeView, TemplateFeatureView

logger = logging.getLogger(__name__)


#------------------------------------------------------------------------------
# Tests
#------------------------------------------------------------------------------

def test_template_controller(template_controller):
    assert template_controller


def test_template_describe(qtbot, template_path):
    with captured_output() as (stdout, stderr):
        template_describe(template_path)
    assert '314' in stdout.getvalue()


def _wait_controller(qtbot, supervisor, gui):
    b = Barrier()
    connect(b('cluster_view'), event='ready', sender=supervisor.cluster_view)
    connect(b('similarity_view'), event='ready', sender=supervisor.similarity_view)
    gui.show()
    qtbot.addWidget(gui)
    qtbot.waitForWindowShown(gui)
    b.wait()


def test_template_gui_0(qtbot, tempdir, template_controller):
    controller = template_controller
    gui = controller.create_gui()
    _wait_controller(qtbot, controller.supervisor, gui)
    gui.close()


def test_template_gui_1(qtbot, tempdir, template_controller):
    controller = template_controller
    gui = controller.create_gui()
    s = controller.supervisor
    _wait_controller(qtbot, controller.supervisor, gui)

    wv = gui.list_views(WaveformView)[0]
    tv = gui.list_views(TraceView)
    if tv:
        tv = tv[0]
        tv.actions.go_to_next_spike()
    else:
        tv = None

    s.actions.next()
    s.block()

    s.actions.move_best_to_good()
    s.block()

    assert len(s.selected) == 1
    s.actions.next()
    s.block()

    clu_to_merge = s.selected
    assert len(clu_to_merge) == 2

    s.actions.merge()
    s.block()

    clu_merged = s.selected[0]
    s.actions.move_all_to_mua()
    s.block()

    s.actions.split_init()
    s.block()

    s.actions.next()
    s.block()

    clu = s.selected[0]
    s.actions.label('some_field', 3)
    s.block()

    s.actions.move_all_to_good()
    s.block()

    wv.actions.toggle_templates(True)
    wv.actions.toggle_mean_waveforms(True)

    s.actions.colormap_rainbow()
    qtbot.wait(100)

    if tv:
        tv.actions.toggle_highlighted_spikes(True)
        tv.actions.go_to_next_spike()
        tv.actions.go_to_previous_spike()
        mouse_click(qtbot, tv.canvas, (100, 100), modifiers=('Control',))
        tv.dock_widget.close()

    assert s.cluster_meta.get('group', clu) == 'good'

    # Emulate filtering in cluster view.
    emit('table_filter', s.cluster_view, s.clustering.cluster_ids[::2])
    qtbot.wait(100)
    emit('table_filter', s.cluster_view, s.clustering.cluster_ids)
    qtbot.wait(100)

    # Emulate sorting in cluster view.
    emit('table_sort', s.cluster_view, s.clustering.cluster_ids[::-1])
    qtbot.wait(100)

    # Test raster view.
    rv = gui.list_views(RasterView)[0]
    s.actions.toggle_categorical_colormap(False)

    mouse_click(qtbot, rv.canvas, (10, 10), modifiers=('Control',))
    qtbot.wait(100)

    rv.dock_widget.close()
    qtbot.wait(100)

    # Test template view.
    tmpv = gui.list_views(TemplateView)[0]
    mouse_click(qtbot, tmpv.canvas, (100, 100), modifiers=('Control',))
    qtbot.wait(100)

    tmpv.dock_widget.close()
    qtbot.wait(100)

    # Save and close.
    s.save()
    gui.close()

    # Create a new controller and a new GUI with the same data.
    params = _read_python(tempdir / 'params.py')
    params['dat_path'] = controller.model.dat_path
    controller = TemplateController(config_dir=tempdir, **params)

    gui = controller.create_gui()
    s = controller.supervisor
    _wait_controller(qtbot, s, gui)

    # Check that the data has been updated.
    assert s.get_labels('some_field')[clu - 1] is None
    assert s.get_labels('some_field')[clu] == '3'

    assert s.cluster_meta.get('group', clu) == 'good'
    for clu in clu_to_merge:
        assert clu not in s.clustering.cluster_ids
    assert clu_merged in s.clustering.cluster_ids

    qtbot.wait(100)
    gui.close()


def test_template_gui_2(qtbot, template_controller):
    gui = template_controller.create_gui()
    _wait_controller(qtbot, template_controller.supervisor, gui)

    gui._create_and_add_view(WaveformView)
    gui._create_and_add_view(ProbeView)

    key_press(qtbot, gui, 'Down')
    key_press(qtbot, gui, 'Down')
    key_press(qtbot, gui, 'Space')
    key_press(qtbot, gui, 'G')
    key_press(qtbot, gui, 'Space')
    key_press(qtbot, gui, 'G', modifiers=('Alt',))
    key_press(qtbot, gui, 'Z')
    key_press(qtbot, gui, 'N', modifiers=('Alt',))
    key_press(qtbot, gui, 'Space')
    key_press(qtbot, gui, 'Enter')
    key_press(qtbot, gui, 'S', modifiers=('Control',))

    gui.close()


def test_template_gui_views(qtbot, template_controller):
    """Test adding new views once clusters are selected."""
    gui = template_controller.create_gui(default_views=())
    _wait_controller(qtbot, template_controller.supervisor, gui)

    template_controller.supervisor.next_best()
    template_controller.supervisor.block()

    template_controller.supervisor.next()
    template_controller.supervisor.block()

    for view_cls in template_controller.view_creator.keys():
        gui._create_and_add_view(view_cls)
        qtbot.wait(100)


def test_template_gui_sim(qtbot, template_controller):
    """Ensure that the similarity is refreshed when clusters change."""
    gui = template_controller.create_gui()
    s = template_controller.supervisor
    _wait_controller(qtbot, s, gui)

    s.cluster_view.sort_by('id', 'desc')
    s.actions.next()
    s.block()

    s.similarity_view.sort_by('id', 'desc')
    cl = 63
    assert s.selected == [cl]
    s.actions.next()
    s.block()

    assert s.selected == [cl, cl - 1]
    s.actions.next()
    s.block()

    assert s.selected == [cl, cl - 2]
    s.actions.merge()
    s.block()

    s.actions.next_best()
    s.block()

    s.actions.next()
    s.block()
    assert s.selected == [cl - 1, cl + 1]

    gui.close()


def test_template_gui_split_amplitude(qtbot, tempdir, template_controller):
    gui = template_controller.create_gui()
    s = template_controller.supervisor
    _wait_controller(qtbot, s, gui)

    s.actions.next()
    s.block()

    av = gui.list_views(AmplitudeView)[0]

    a, b = 50, 1000
    mouse_click(qtbot, av.canvas, (a, a), modifiers=('Control',))
    mouse_click(qtbot, av.canvas, (a, b), modifiers=('Control',))
    mouse_click(qtbot, av.canvas, (b, b), modifiers=('Control',))
    mouse_click(qtbot, av.canvas, (b, a), modifiers=('Control',))

    n = max(s.clustering.cluster_ids)

    s.actions.split()
    s.block()

    # Split one cluster => Two new clusters should be selected after the split.
    assert s.selected_clusters == [n + 1, n + 2]

    # qtbot.stop()
    gui.close()


def test_template_gui_split_template_feature(qtbot, tempdir, template_controller):
    gui = template_controller.create_gui()
    s = template_controller.supervisor
    _wait_controller(qtbot, s, gui)

    s.actions.next()
    s.block()
    s.actions.next()
    s.block()

    assert len(s.selected) == 2

    tfv = gui.list_views(TemplateFeatureView)
    if not tfv:
        return
    tfv = tfv[0]

    a, b = 0, 1000
    mouse_click(qtbot, tfv.canvas, (a, a), modifiers=('Control',))
    mouse_click(qtbot, tfv.canvas, (a, b), modifiers=('Control',))
    mouse_click(qtbot, tfv.canvas, (b, b), modifiers=('Control',))
    mouse_click(qtbot, tfv.canvas, (b, a), modifiers=('Control',))

    n = max(s.clustering.cluster_ids)

    s.actions.split()
    s.block()

    assert s.selected_clusters == [n + 1]

    # qtbot.stop()
    gui.close()


def test_template_amplitude(template_controller):
    controller = template_controller
    s = controller.supervisor
    b = s.merge([31, 51])
    amp = controller.get_cluster_amplitude(b.added[0])
    assert amp > 0
