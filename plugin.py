import sublime

from LSP.plugin import register_plugin, unregister_plugin
from LSP.plugin import AbstractPlugin

class OcamlLspPlugin(AbstractPlugin):
	@classmethod
	def name(cls):
		return "OCaml"

def plugin_loaded():
	register_plugin(OcamlLspPlugin)

def plugin_unloaded():
	unregister_plugin(OcamlLspPlugin)