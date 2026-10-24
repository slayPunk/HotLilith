import gi
import sys
from pathlib import Path
gi.require_version('Gtk','4.0')
from gi.repository import Gtk,GLib
app=Gtk.Application(application_id='org.hotlilit.Placement')
def activate(app):
 parent=Gtk.ApplicationWindow(application=app,title='placement-parent',default_width=480,default_height=320)
 parent.set_child(Gtk.Label(label='Parent application'))
 parent.present()
 def poll():
  trigger=Path(sys.argv[1])
  if trigger.exists():
   trigger.unlink()
   dialog=Gtk.Window(title='placement-dialog',transient_for=parent,modal=True,default_width=260,default_height=160)
   dialog.set_child(Gtk.Label(label='A dialog follows its parent'))
   dialog.present()
   return True
  return True
 GLib.timeout_add(100,poll)
app.connect('activate',activate)
app.run([])
