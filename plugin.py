import os

import sublime
import sublime_plugin

from LSP.plugin import register_plugin, unregister_plugin
from LSP.plugin import AbstractPlugin
from LSP.plugin import Request

from LSP.plugin.core.protocol import DocumentUri, Range
from LSP.plugin.core.registry import LspTextCommand
from LSP.plugin.core.typing import Optional, List, Tuple
from LSP.plugin.core.url import parse_uri
from LSP.plugin.core.views import uri_from_view, range_to_region

class OcamlLspPlugin(AbstractPlugin):
	@classmethod
	def name(cls) -> str:
		return "OCaml"

class ExperimentalLsp(LspTextCommand):
	session_prefix = "experimental.ocamllsp."

	def get_local_path(self, path: str) -> str:
		return os.path.basepath(path)

	def on_infer_int_async(self, result: Optional[str]) -> None:
		if result is None:
			return
		window = self.view.window()
		if window is None:
			return
		sheets = window.selected_sheets()
		view = window.new_file(flags=sublime.TRANSIENT)
		view.assign_syntax("scope:source.ocaml")
		view.set_scratch(False)
		view.set_name(self.file_name)
		view.run_command("append", {"characters": result})
		sheet = view.sheet()
		if sheet is not None:
			sheets.append(sheet)
			window.select_sheets(sheets)

	def handle_infer_intf(self, view: sublime.View) -> None:
		session = self.best_session(self.session_prefix+"handleInferIntf")
		if session is None:
			return
		params = uri_from_view(view)
		session.send_request_async(Request("ocamllsp/inferIntf", [params]), self.on_infer_int_async)

class InferIntfCommand(ExperimentalLsp):
	def name(cls) -> str:
		return "InferIntf"

	def run(self, edit: sublime.Edit) -> None:
		view = self.view
		file_name = view.file_name()
		if file_name is None:
			return
		self.file_name = os.path.basepath(file_name)+ 'i'
		self.handle_infer_intf(view)

class SwitchImplIntf(ExperimentalLsp):
	def name(cls) -> str:
		return "SwitchImplIntf"

	def open_file(self, option: int) -> None:
		if option == -1:
			return
		window = self.window
		opt = self.items[option]
		current_path = os.getcwd() + opt
		if os.path.exists(current_path) is False:
			self.file_name = opt
			self.handle_infer_intf(self.view)
			return
		view = window.open_file(self.items[option])
		view.assign_syntax("scope:source.ocaml")
		sheets = window.selected_sheets()
		sheet = view.sheet()
		if sheet is not None:
			sheets.append(sheet)
			window.select_sheets(sheets)

	def to_quick_panel_item(self, uri: DocumentUri) -> Tuple[str, sublime.QuickPanelItem]:
		full_path = parse_uri(uri)[1]
		base_name = os.path.basename(full_path)
		return (base_name, sublime.QuickPanelItem(
			trigger=base_name,
			details=full_path))

	def handle_switch_async(self, uris: List[DocumentUri]) -> None:
		window = self.view.window()
		if window is None:
			return
		self.window = window
		tuple_list = [self.to_quick_panel_item(uri) for uri in uris]
		self.items, quick_panel_items = zip(*tuple_list)
		window.show_quick_panel(quick_panel_items, self.open_file)

	def run(self, edit: sublime.Edit) -> None:
		session = self.best_session(self.session_prefix+"handleSwitchImplIntf")
		if session is None:
			return
		params = uri_from_view(self.view)
		session.send_request_async(Request("ocamllsp/switchImplIntf", [params]), self.handle_switch_async)


'''
class TypedHolesCommand(LspTextCommand):
	def name(cls) -> str:
		return "TypedHoles"

	def small_html(annotation) -> str:
		return '<small style="font-family: system">{}</small>'.format(annotation)

	def on_typed_holes_async(self, ranges: List[Range]) -> None:
		for range_ in ranges:
			range_lsp = Range.from_lsp(range_)
			region = range_to_region(range_lsp, self.view)
			content = self.small_html(range_["command"]["title"])
			self.phantoms.append(sublime.Phantom(region, content, sublime.LAYOUT_BELOW))
		self.phantom_set.update(self.phantoms)

	def run(self, edit: sublime.Edit) -> None:
		capability = self.session_by_name("experimental.ocamllsp.inferIntf")

		session = self.session_by_name("handleInferIntf")
		if session is None:
			raise Exception("Hi")
			return
		params = text_document_identifier(self.view)
		session.send_request_async(Request("ocamllsp/typedHoles", params), self.on_typed_holes_async)
'''

def plugin_loaded():
	register_plugin(OcamlLspPlugin)

def plugin_unloaded():
	unregister_plugin(OcamlLspPlugin)