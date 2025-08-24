#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject

import os
import subprocess


HERE = os.path.abspath(os.path.dirname(__file__))
HELPER = os.path.join(HERE, 'swapctl.sh')
# Prefer installed helper if present for better pkexec branding via polkit
INSTALLED_HELPER = "/usr/local/lib/swap-manager/swapctl.sh"
if os.path.exists(INSTALLED_HELPER):
    HELPER = INSTALLED_HELPER


def read_proc_swaps():
    entries = []
    try:
        with open('/proc/swaps', 'r') as f:
            lines = f.read().strip().splitlines()
        # Header: Filename	Type	Size	Used	Priority
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 5:
                filename, typ, size_kb, used_kb, prio = parts[:5]
                entries.append({
                    'path': filename,
                    'type': typ,
                    'size_mib': int(int(size_kb) / 1024),
                    'used_mib': int(int(used_kb) / 1024),
                    'priority': int(prio),
                    'active': True,
                })
    except Exception:
        pass
    return entries


def get_swappiness():
    try:
        with open('/proc/sys/vm/swappiness', 'r') as f:
            return int(f.read().strip())
    except Exception:
        return None


def run_helper(args, require_root=True):
    # Returns (stdout, stderr, exitcode)
    argv = []
    if os.geteuid() == 0 or not require_root:
        argv = [HELPER] + args
    else:
        argv = ['pkexec', HELPER] + args
    try:
        proc = subprocess.run(argv, check=False, capture_output=True, text=True)
        return proc.stdout.strip(), proc.stderr.strip(), proc.returncode
    except FileNotFoundError as e:
        return '', str(e), 127


class SwapManager(Gtk.Window):
    def __init__(self):
        super().__init__(title='Swap Manager')
        self.set_default_size(760, 520)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, border_width=8)
        self.add(outer)

        # Toolbar
        toolbar = Gtk.Box(spacing=6)
        outer.pack_start(toolbar, False, False, 0)

        btn_refresh = Gtk.Button(label='Refresh')
        btn_refresh.connect('clicked', lambda *_: self.refresh())
        toolbar.pack_start(btn_refresh, False, False, 0)

        self.status_label = Gtk.Label(label='')
        self.status_label.set_xalign(0.0)
        toolbar.pack_start(self.status_label, True, True, 8)

        # Swap list
        self.store = Gtk.ListStore(str, str, int, int, int, bool)
        # Columns: Path, Type, SizeMiB, UsedMiB, Priority, Active
        tree = Gtk.TreeView(model=self.store)
        cols = [
            ('Path', 0),
            ('Type', 1),
            ('Size (MiB)', 2),
            ('Used (MiB)', 3),
            ('Priority', 4),
            ('Active', 5),
        ]
        for title, idx in cols:
            renderer = Gtk.CellRendererText()
            col = Gtk.TreeViewColumn(title, renderer, text=idx)
            col.set_sort_column_id(idx)
            tree.append_column(col)
        sel = tree.get_selection()
        sel.set_mode(Gtk.SelectionMode.SINGLE)
        outer.pack_start(tree, True, True, 0)

        # Actions row
        actions = Gtk.Box(spacing=6)
        outer.pack_start(actions, False, False, 0)

        self.btn_enable = Gtk.Button(label='Enable')
        self.btn_enable.connect('clicked', self.on_enable)
        actions.pack_start(self.btn_enable, False, False, 0)

        self.btn_disable = Gtk.Button(label='Disable')
        self.btn_disable.connect('clicked', self.on_disable)
        actions.pack_start(self.btn_disable, False, False, 0)

        # Create swapfile
        frame_create = Gtk.Frame(label='Create Swap File')
        outer.pack_start(frame_create, False, False, 0)
        grid = Gtk.Grid(column_spacing=10, row_spacing=6, border_width=8)
        frame_create.add(grid)

        self.entry_path = Gtk.Entry()
        self.entry_path.set_text('/swapfile')
        self.spin_size = Gtk.SpinButton.new_with_range(1, 1048576, 1)
        self.spin_size.set_value(2048)
        self.chk_persist = Gtk.CheckButton(label='Persist in fstab')
        btn_create = Gtk.Button(label='Create')
        btn_create.connect('clicked', self.on_create)

        grid.attach(Gtk.Label(label='Path:'), 0, 0, 1, 1)
        grid.attach(self.entry_path, 1, 0, 1, 1)
        grid.attach(Gtk.Label(label='Size (MiB):'), 0, 1, 1, 1)
        grid.attach(self.spin_size, 1, 1, 1, 1)
        grid.attach(self.chk_persist, 1, 2, 1, 1)
        grid.attach(btn_create, 1, 3, 1, 1)

        # Remove swapfile
        frame_remove = Gtk.Frame(label='Remove Swap File')
        outer.pack_start(frame_remove, False, False, 0)
        grid2 = Gtk.Grid(column_spacing=10, row_spacing=6, border_width=8)
        frame_remove.add(grid2)

        self.chk_remove_fstab = Gtk.CheckButton(label='Also remove from fstab')
        btn_remove = Gtk.Button(label='Remove selected file')
        btn_remove.connect('clicked', self.on_remove)
        grid2.attach(self.chk_remove_fstab, 0, 0, 1, 1)
        grid2.attach(btn_remove, 0, 1, 1, 1)

        # Swappiness
        frame_sw = Gtk.Frame(label='Swappiness')
        outer.pack_start(frame_sw, False, False, 0)
        grid3 = Gtk.Grid(column_spacing=10, row_spacing=6, border_width=8)
        frame_sw.add(grid3)

        self.spin_swappiness = Gtk.SpinButton.new_with_range(0, 200, 1)
        btn_apply_sw = Gtk.Button(label='Apply')
        btn_apply_sw.connect('clicked', self.on_apply_swappiness)
        self.lbl_sw_current = Gtk.Label(label='Current: ?')
        self.lbl_sw_current.set_xalign(0.0)

        grid3.attach(Gtk.Label(label='vm.swappiness:'), 0, 0, 1, 1)
        grid3.attach(self.spin_swappiness, 1, 0, 1, 1)
        grid3.attach(btn_apply_sw, 2, 0, 1, 1)
        grid3.attach(self.lbl_sw_current, 0, 1, 3, 1)

        self.refresh()

    def get_selected_path(self):
        sel = self.get_child().get_children()[1].get_selection()  # TreeView is second child (index 1)
        model, itr = sel.get_selected()
        if itr:
            return model[itr][0], model[itr][1]
        return None, None

    def refresh(self):
        self.store.clear()
        entries = read_proc_swaps()
        for e in entries:
            self.store.append([e['path'], e['type'], e['size_mib'], e['used_mib'], e['priority'], e['active']])
        sw = get_swappiness()
        if sw is not None:
            self.lbl_sw_current.set_text(f'Current: {sw}')
            self.spin_swappiness.set_value(sw)
        self.status_label.set_text(f"Active swaps: {len(entries)}")

    def message(self, text, error=False):
        dialog = Gtk.MessageDialog(parent=self, flags=0,
                                   message_type=Gtk.MessageType.ERROR if error else Gtk.MessageType.INFO,
                                   buttons=Gtk.ButtonsType.OK, text=text)
        dialog.run()
        dialog.destroy()

    def on_enable(self, _btn):
        path, _typ = self.get_selected_path()
        if not path:
            self.message('Select a swap entry to enable.')
            return
        out, err, rc = run_helper(['enable', path])
        if rc != 0:
            self.message(f'Enable failed:\n{err or out}', error=True)
        else:
            self.refresh()

    def on_disable(self, _btn):
        path, _typ = self.get_selected_path()
        if not path:
            self.message('Select a swap entry to disable.')
            return
        out, err, rc = run_helper(['disable', path])
        if rc != 0:
            self.message(f'Disable failed:\n{err or out}', error=True)
        else:
            self.refresh()

    def on_create(self, _btn):
        path = self.entry_path.get_text().strip()
        size_mib = int(self.spin_size.get_value())
        args = ['create-file', path, str(size_mib)]
        if self.chk_persist.get_active():
            args.append('--persist')
        out, err, rc = run_helper(args)
        if rc != 0:
            self.message(f'Create failed:\n{err or out}', error=True)
        else:
            self.refresh()

    def on_remove(self, _btn):
        path, typ = self.get_selected_path()
        if not path:
            self.message('Select a swap entry to remove.')
            return
        if typ != 'file':
            self.message('Remove only supports swap files (not partitions).', error=True)
            return
        args = ['delete-file', path]
        if self.chk_remove_fstab.get_active():
            args.append('--remove-fstab')
        out, err, rc = run_helper(args)
        if rc != 0:
            self.message(f'Remove failed:\n{err or out}', error=True)
        else:
            self.refresh()

    def on_apply_swappiness(self, _btn):
        val = int(self.spin_swappiness.get_value())
        out, err, rc = run_helper(['set-swappiness', str(val)])
        if rc != 0:
            self.message(f'Set swappiness failed:\n{err or out}', error=True)
        else:
            self.refresh()


def main():
    win = SwapManager()
    win.connect('destroy', Gtk.main_quit)
    win.show_all()
    Gtk.main()


if __name__ == '__main__':
    main()
