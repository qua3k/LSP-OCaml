import os

import sublime
import sublime_plugin

from functools import partial

from LSP.plugin import register_plugin, unregister_plugin
from LSP.plugin import AbstractPlugin
from LSP.plugin import Request

from LSP.plugin.core.protocol import DocumentFilter, DocumentUri, Range, Response
from LSP.plugin.core.registry import LspTextCommand
from LSP.plugin.core.typing import Optional, List, Tuple
from LSP.plugin.core.url import parse_uri
from LSP.plugin.core.views import text_document_identifier, uri_from_view, range_to_region

OCAML_SYNTAX = "scope:source.ocaml"

class OcamlLspPlugin(AbstractPlugin):
    @classmethod
    def name(cls) -> str:
        return "OCaml"

class ExperimentalLsp(LspTextCommand):
    capability = None

    def is_enabled(self) -> bool:
        return super().is_enabled() or bool(self.best_session(self.capability))

    def send_custom_async(self, request: str, params, callback) -> None:
        session = self.best_session(self.capability)
        if session is not None:
            session.send_request_async(Request(request, params), callback)

class InferIntfCommand(ExperimentalLsp):
    capability = "experimental.ocamllsp.handleInferIntf"

    def name(cls) -> str:
        return "InferIntf"

    def append_view_sheet(self, window: sublime.Window, view: sublime.View) -> None:
        sheets = window.selected_sheets()
        sheet = view.sheet()
        if sheet is not None:
            sheets.append(sheet)
            window.select_sheets(sheets)


    def on_infer_int_async(self, result: Optional[str]) -> None:
        if result is None:
            return
        window = self.view.window()
        if window is None:
            return

        view = window.new_file(flags=sublime.TRANSIENT)
        view.assign_syntax(OCAML_SYNTAX)
        view.set_scratch(False)
        view.set_name(self.base_path)
        view.run_command("append", {"characters": result})
        self.append_view_sheet(window, view)

    def send_infer_async(self) -> None:
        self.send_custom_async("ocamllsp/inferIntf", [uri_from_view(self.view)],
            self.on_infer_int_async)

    def run(self, edit: sublime.Edit) -> None:
        file_name = self.view.file_name()
        if file_name is not None:
            self.base_path = "{}i".format(os.path.basename(file_name))
            self.send_infer_async()

class SwitchImplIntf(InferIntfCommand):
    capability = "experimental.ocamllsp.handleSwitchImplIntf"

    def name(cls) -> str:
        return "SwitchImplIntf"

    def open_file(self, option: int) -> None:
        if option == -1:
            return
        selection = self.uris[option]
        full_path = selection.details
        if not os.path.exists(full_path):
            self.base_path = selection.trigger
            return self.send_infer_async()
        window = self.window
        view = window.open_file(selection.trigger)
        view.assign_syntax(OCAML_SYNTAX)
        self.append_view_sheet(window, view)

    def to_quick_panel_item(uri: DocumentUri) -> sublime.QuickPanelItem:
        full_path = parse_uri(uri)[1]
        base_path = os.path.basename(full_path)
        return sublime.QuickPanelItem(
            details=full_path,
            trigger=base_path)

    def handle_switch_async(self, uris: List[DocumentUri]) -> None:
        window = self.view.window()
        if window is not None:
            self.uris = [to_quick_panel_item(uri) for uri in uris]
            window.show_quick_panel(self.items, self.open_file)


    def run(self, edit: sublime.Edit) -> None:
        self.send_custom_async("ocamllsp/switchImplIntf", [uri_from_view(self.view)],
            self.handle_switch_async)

class TypedHolesCommand(ExperimentalLsp):
    capability = "experimental.ocamllsp.handleTypedHoles"

    def region_end(self, region: sublime.Region) -> int:
        return region.end()

    def jump_to_hole_async(self, previous: bool, ranges: List[Range]) -> None:
        positions = self.view.sel()
        if not len(positions):
            return
        start = positions[0].begin()

        regions = [range_to_region(range_, self.view) for range_ in ranges]
        regions.sort(key=self.region_end)
        region_length = len(regions)
        if not region_length:
            return

        selected_region = regions[0 if previous else region_length-1]
        if previous == True:
            for region in regions:
                if region.begin() > start:
                    break
                selected_region = region
        else:
            for region in regions:
                if region.begin() > start:
                    selected_region = region
                    break
        self.view.sel().clear()
        self.view.sel().add(selected_region)

class PreviousTypedHoleCommand(TypedHolesCommand):
    def name(cls) -> str:
        return "PreviousTypedHole"

    def run(self, edit: sublime.Edit) -> None:
        self.send_custom_async("ocamllsp/typedHoles", text_document_identifier(self.view),
            partial(self.jump_to_hole_async, True))

class NextTypedHoleCommand(TypedHolesCommand):
    def name(cls) -> str:
        return "NextTypedHole"

    def run(self, edit: sublime.Edit) -> None:
        self.send_custom_async("ocamllsp/typedHoles", text_document_identifier(self.view),
            partial(self.jump_to_hole_async, False))

def plugin_loaded():
    register_plugin(OcamlLspPlugin)

def plugin_unloaded():
    unregister_plugin(OcamlLspPlugin)