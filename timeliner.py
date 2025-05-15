import tkinter as tk
from tkinter import ttk
from tkinter import filedialog


import sys
import pandas as pd
import platform
from datetime import datetime
from dateutil.relativedelta import relativedelta
from typing import Optional

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
from matplotlib.ticker import FixedLocator

from ipydex import IPS




class TimelineEditor(tk.Tk):
    '''Window to enter timeline data. Creates timeline image and inserts data 
    to inspection database on OK'''
    name_col = 0
    interval_col = 1
    dates_col = 2

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title('Zeitstrahl erzeugen')
        self.minsize(800, 500)
        self.lines = []
        self.in_displaying = False             # flag for automatically updating preview, used only internally to avoid focussing out of an entry...
        self.figure = None
        self.curr_tl = None

        self.allfrm = ttk.Frame(self)
        scrl = ScrollFrame(self.allfrm, orient='horizontal', def_width=800)
        self.workfrm = scrl.viewPort
        self.curr_row = 0
        
        self.btnsfrm = ttk.Frame(self.allfrm)
        self.previewfrm = ttk.Frame(self.allfrm)
        self.build_structure()

        self.allfrm.pack(fill='both', expand=True, padx=1, pady=1)
        scrl.pack(fill='both', expand=True, padx=1, pady=1)
        self.btnsfrm.pack(fill='x', padx=1, pady=1)
        self.previewfrm.pack(fill='x', padx=1, pady=1)

        self.bind('<Control-Return>', lambda *_: self.save())
        self.focus()


    def build_structure(self):       
        # info
        ttk.Label(self.allfrm, text='Name der Arbeit: Absatz durch "|" erzeugen.')\
            .pack(padx=1, pady=1, fill='x', anchor='w')
        ttk.Label(self.allfrm, text='Intervall: in Monaten, nur ganze Zahlen oder leer')\
            .pack(padx=1, pady=1, fill='x', anchor='w')
        ttk.Label(self.allfrm, text='Daten: Format mm/yy, z.B. 03/24')\
            .pack(padx=1, pady=1, fill='x', anchor='w')
        
        ttk.Separator(self.allfrm).pack(fill='x', padx=1, pady=1)
        
        # entries for start/end entering
        startendfrm = ttk.Frame(self.workfrm)
        startendfrm.grid(row=self.curr_row, column=0, columnspan=3,
                         padx=1, pady=1, sticky='ew')
        self.startstrvar = tk.StringVar(self)
        self.endstrvar = tk.StringVar(self)
        ttk.Label(startendfrm, text='Start:    ')\
            .grid(row=0, column=0, padx=1, pady=1)
        ttk.Entry(startendfrm, textvariable=self.startstrvar)\
            .grid(row=0, column=1, padx=1, pady=1)
        ttk.Label(startendfrm, text='Ende:    ')\
            .grid(row=1, column=0, padx=1, pady=1)
        ttk.Entry(startendfrm, textvariable=self.endstrvar)\
            .grid(row=1, column=1, padx=1, pady=1)
        
        self.curr_row += 1
        ttk.Separator(self.workfrm).grid(row=self.curr_row, column=0, columnspan=3,
                                         padx=1, pady=1, sticky='ew')
        self.curr_row += 1
        
        # make header
        ttk.Label(self.workfrm, text='Titel')\
            .grid(row=self.curr_row, column=self.name_col, padx=1, pady=1, sticky='w')
        ttk.Label(self.workfrm, text='Intervall')\
            .grid(row=self.curr_row, column=self.interval_col, padx=1, pady=1, sticky='w')
        ttk.Label(self.workfrm, text='Daten')\
            .grid(row=self.curr_row, column=self.dates_col, padx=1, pady=1, sticky='w')
        self.workfrm.grid_columnconfigure(self.dates_col, weight=100)

        # lines for dates entering
        self.curr_row += 1
        self.lines.append(single_timeLine(self, self.curr_row))
        self.curr_row += 1

        ttk.Button(self.btnsfrm, text='OK', command=self.save)\
            .pack(side='right', padx=1, pady=1)
        ttk.Button(self.btnsfrm, text='Vorschau', command=self.display_preview)\
            .pack(side='right', padx=1, pady=1)

    def add_newline_if_full(self, *_):
        for line in self.lines:
            if not line.get_title(): return
        self.lines.append(single_timeLine(self, self.curr_row))
        self.curr_row += 1
    
    def get_timeline_dict(self):
        _, end = self.get_startend()
        end = monthyear2datetime(end)
        tl_dict = {}
        for line in self.lines:
            if not line.has_dates(): continue
            title = line.get_title(empty_allowed=False)
            dates = line.get_dateslist()
            for i, datestr in enumerate(dates):
                if i == 0 and isinstance(dates[0], int): continue 
                date = monthyear2datetime(datestr)
                if date > end:
                    dates.remove(datestr)
                    ErrorWindow(self, f'{title}: Datum {datestr} wird ignoriert (neuer als Enddatum).')
            tl_dict[title] = dates
        return tl_dict
    
    def get_startend(self):
        def get_single(what='start'):
            if what == 'start': strvar = self.startstrvar
            elif what == 'end': strvar = self.endstrvar
            else: raise AttributeError(f'what must be start or end, not {what}')

            if not (txt := strvar.get().strip()): return txt
            # test for right format
            monthyear2datetime(txt)
            return txt
        return get_single('start'), get_single('end')
    
    def save(self):
        '''saves timeline as image and in inspection's database'''
        try:
            start, end = self.get_startend()
        except Exception as e:
            ErrorWindow(self, (f'Fehler in Start/Ende Textboxen. Ist das Format mm/yy (z. B. 11/22)?\n'
                               f'Fehlertext: {e}'))
            return
        if not start or not end:
            ErrorWindow(self, 'Bitte Start und Ende angeben')
            return
        try: tl_dict = self.get_timeline_dict()
        except Exception as e:
            ErrorWindow(self, f'Zeitstrahlfehler: {e}')
            return
                
        if len(tl_dict) == 0: self.destroy()
        self.save_timeline()
        self.destroy()
        sys.exit()

    def display_preview(self, *_):
        self.in_displaying = True
        curr_focus = self.focus_get()
        delete_children(self.previewfrm)
        fig = self.get_figure()
        canvas = FigureCanvasTkAgg(fig, master=self.previewfrm)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True, padx=3, pady=3)
        self.update()
        try: curr_focus.focus()
        except AttributeError: pass
        self.in_displaying = False

    def save_timeline(self, name='timeline'):
        '''saves the timeline figure in a selectable selected folder'''
        fig = self.get_figure()
        path = filedialog.askdirectory(parent=self)
        path = f'{path}/{name}.jpg'
         
        fig.savefig(path, dpi=300)
    
    def get_figure(self):
        '''return pyplot figure showing the timeline'''

        timeline_data, start, end = self.get_timeline_dict(), *self.get_startend()

        if self.figure: plt.close(self.figure)

        mpl.rcParams['font.sans-serif'] = 'Arial'
        mpl.rcParams['font.family'] = 'sans-serif'
        for fontsize in ['font.size', 'axes.titlesize',
                        'axes.labelsize', 'xtick.labelsize']:
            plt.rcParams.update({fontsize: 11})


        keys = list(timeline_data.keys())
        nrows = len(keys)

        # Convert start and end dates to datetime objects
        start_date = datetime.strptime(start, '%m/%y')
        end_date = datetime.strptime(end, '%m/%y')

        # Create figure and axis
        fig, ax = plt.subplots(figsize=(5.5, .5+nrows/3), layout='constrained')    
        # format axis
        ax.spines[['top', 'left', 'right', 'bottom']].set_visible(False)
        # Assign y positions to each key
        y_positions = list(range(nrows))
        ax.set_yticks(y_positions)
        ax.set_ylim([-nrows/10, y_positions[-1]+nrows/10])
        ax.set_yticklabels([key.replace('|', '\n') for key in keys])
        ax.invert_yaxis()  # Top key first
        ax.tick_params(axis='y', which='both', length=0)

        # Set x-axis limits and format
        datespan = (end_date-start_date).days / 30 # months
        ax.set_xlim(start_date-relativedelta(months=1), end_date+relativedelta(months=round(datespan/20)))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%y'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        ax.tick_params(axis='x', which='both', direction='inout', length=6, labelrotation=45)

        # Custom x-ticks handling    
        # Get potential ticks then filter
        raw_ticks = mdates.AutoDateLocator().tick_values(start_date, end_date)
        min_distance = round(datespan*1.5)  # Minimum days between edge ticks and first/last interior ticks
        
        # Convert to datetime and filter
        filtered_ticks = []
        for tick in raw_ticks:
            tick_date = mdates.num2date(tick).replace(tzinfo=None)
            if tick_date < start_date or tick_date > end_date:
                continue
                
            # Check proximity to edges
            days_from_start = (tick_date - start_date).days
            days_from_end = (end_date - tick_date).days
            
            # Always keep start/end dates
            if days_from_start == 0 or days_from_end == 0:
                filtered_ticks.append(tick_date)
                continue
                
            # Filter nearby ticks
            if days_from_start > min_distance and days_from_end > min_distance:
                filtered_ticks.append(tick_date)
        
        # Ensure start/end are always included
        filtered_dates = [start_date, end_date] + [
            t for t in filtered_ticks 
            if t not in {start_date, end_date}
        ]
        filtered_dates.sort()

        ax.xaxis.set_major_locator(FixedLocator(mdates.date2num(filtered_dates)))
        ax.tick_params(axis='x', which='both', direction='inout', length=6, labelrotation=45)


        # Plot each entry
        for y_pos, key in zip(y_positions, keys):
            entry = timeline_data[key]
            interval = None
            date_strs = entry
            
            # Check if the first element is an interval (integer)
            if isinstance(entry[0], int):
                interval = entry[0]
                date_strs = entry[1:]
            
            # Convert date strings to datetime objects
            dates_list = [datetime.strptime(ds, '%m/%y') for ds in date_strs]
            
            # Plot vertical markers
            for date in dates_list:
                ax.plot(date, y_pos, 'k|', markersize=8, markeredgewidth=2, zorder=3)
            
            # Plot blue interval lines
            if interval is not None:
                for date in dates_list:
                    end_date_line = min([date + relativedelta(months=+interval),
                                        end_date])
                    ax.hlines(
                        y=y_pos, xmin=date, xmax=end_date_line,
                        colors='tab:blue', linewidth=2, alpha=0.35, zorder=2)
        for date in [start_date, end_date]:
            ax.axvline(date, c='tab:gray', ls='--', lw=1, zorder=1, alpha=.5)


        # add arrow as x axis
        xmin, xmax = ax.get_xlim()
        ymin, _ = ax.get_ylim()
        arrow = mpatches.FancyArrowPatch(
            (xmin, ymin), (xmax, ymin),
            arrowstyle='-|>',
            mutation_scale=10,
            color='black',
            linewidth=0.8,
            clip_on=False
        )
        ax.add_patch(arrow)
        self.figure = fig
        return fig
    

class single_timeLine():
    def __init__(self, master: TimelineEditor, row: int,
                 prefill: Optional[list]=None):
        self.master = master
        self.row = row

        try: title = prefill[0]
        except IndexError: title=None
        except TypeError: title=None
        self.titlevar = tk.StringVar(self.master, value=title)
        self.titlevar.trace_add('write', self.master.add_newline_if_full)
        
        try: interval = int(prefill[1][0])
        except ValueError: interval = None
        except IndexError: interval = None
        except TypeError: interval = None
        self.intervalvar = tk.StringVar(self.master, value=interval)

        self.datevars = []

        # entries
        self.titleentry = ttk.Entry(self.master.workfrm,
                                textvariable=self.titlevar)
        self.intervalentry = ttk.Entry(self.master.workfrm,
                                    textvariable=self.intervalvar, width=4)
        self.datesfrm = ttk.Frame(self.master.workfrm)
        if prefill:
            dates = prefill[1][1:] if interval else prefill[1]
            for i, date in enumerate(dates):
                self.add_single_datecol(i, prefill_date=date)

        self.titleentry.grid(row=self.row, column=self.master.name_col,
                             padx=1, pady=1, sticky='ew')
        self.intervalentry.grid(row=self.row, column=self.master.interval_col,
                                padx=1, pady=1, sticky='ew')
        self.datesfrm.grid(row=self.row, column=self.master.dates_col,
                           padx=1, pady=1, sticky='ew')

        self.add_datecol_if_full()

    def add_datecol_if_full(self, *_):
        i = 0
        for datevar in self.datevars:
            if not datevar.get(): return
            i += 1
        self.add_single_datecol(i)
    
    def add_single_datecol(self, col, prefill_date: Optional[str]=None):
        datestrvar = tk.StringVar(self.master, value=prefill_date)
        datestrvar.trace_add('write', self.add_datecol_if_full)
        dateentry = ttk.Entry(self.datesfrm, textvariable=datestrvar, width=10)
        dateentry.grid(row=0, column=col, padx=1, pady=1, sticky='ew')
        dateentry.bind('<Tab>', self.update_preview)
        self.datevars.append(datestrvar)

    def update_preview(self, *_):
        if self.master.in_displaying: return
        try: self.master.display_preview()
        except Exception as e: print(e)
        finally: self.master.in_displaying = False

    def get_title(self, empty_allowed=True):
        title = self.titlevar.get().strip()
        if empty_allowed: return title
        if not title:
            raise ValueError('Title can\'t be empty.')
        return title
    def get_dateslist(self):
        if not self.has_dates(): return []
        try: title = self.get_title()
        except ValueError as e:
            ErrorWindow(self.master,
                        'Alle Titel bei eingetragenen Daten müssen ausgefüllt sein.',
                        self.titleentry.focus())
            raise e
        interval = self.intervalvar.get().strip()
        if interval:
            try: interval = int(interval)
            except ValueError as e:
                ErrorWindow(self.master,
                    f'Intervall muss zahlwertig oder leer sein ({title}).',
                    self.intervalentry.focus())
                raise e
            ret_list = [interval]
        else: ret_list = []
        for datevar in self.datevars:
            date = datevar.get().strip()
            if not date: continue
            try: monthyear2datetime(date)
            except Exception as e:
                ErrorWindow(self.master,
                            (f'Fehler beim Konvertieren von {date} zu einem Datum. '
                             'Ist das Format mm/yy (z. B. 05/21)?\n'
                             f'Fehlernachricht: {e}'))
                raise e
            ret_list.append(date)
        return ret_list

    def has_dates(self):
        for datevar in self.datevars:
            if datevar.get().strip(): return True
        return False


class ErrorWindow(tk.Toplevel):
    '''simple window for showing some text'''
    def __init__(self, master, text, on_end=None) -> None:
        super().__init__(master)
        self.text=text
        self.on_end = on_end

        self.workfrm = ttk.Frame(self)
        self.errlbl = ttk.Label(self.workfrm, text=self.text)
        self.okbtn = ttk.Button(self.workfrm, text='OK',
                                command=self.end)

        self.workfrm.grid(sticky='nsew')
        self.errlbl.grid(row=0, column=0, sticky='ew', padx=3, pady=3)
        self.okbtn.grid(row=1, column=0, sticky='e', padx=3, pady=3)
        self.bind('<Escape>', self.end)
        self.bind('<Return>', self.end)
        self.okbtn.focus()
        
    def end(self, *args):
        if self.on_end is not None:
            self.on_end()
        self.destroy()


class ScrollFrame(tk.Frame):
    def __init__(self, parent, orient='vertical', use_mousewheel=True,
                 def_height=None, def_width=None):
        super().__init__(parent) # create a frame (self)
        
        self.orient = orient
        self.canvas = tk.Canvas(self, borderwidth=0, 
                                height=def_height, width=def_width)                     #place canvas on self
        self.viewPort = ttk.Frame(self.canvas)                                           #place a frame on the canvas, this frame will hold the child widgets 

        if self.orient == 'vertical':
            self.vsb = tk.Scrollbar(self, orient=orient, command=self.canvas.yview)     #place a scrollbar on self 
            self.canvas.configure(yscrollcommand=self.vsb.set)                          #attach scrollbar action to scroll of canvas

            self.vsb.pack(side="right", fill="y")                                       #pack scrollbar to right of self
            self.canvas.pack(side="right", fill="both", expand=True)                     #pack canvas to left of self and expand to fil

        elif orient == 'horizontal':
            self.hsb = tk.Scrollbar(self, orient=orient, command=self.canvas.xview) #place a scrollbar on self 
            self.canvas.configure(xscrollcommand=self.hsb.set)                          #attach scrollbar action to scroll of canvas

            self.hsb.pack(side="bottom", fill="x")                                       #pack scrollbar to right of self
            self.canvas.pack(side="left", fill="both", expand=True)                     #pack canvas to left of self and expand to fil


        self.canvas_window = self.canvas.create_window((4,4),
                                            window=self.viewPort, anchor="nw",            #add view port frame to canvas
                                            tags="self.viewPort")

        self.viewPort.bind("<Configure>", self.onFrameConfigure)                       #bind an event whenever the size of the viewPort frame changes.
        self.canvas.bind("<Configure>", self.onCanvasConfigure)                       #bind an event whenever the size of the canvas frame changes.
        
        if use_mousewheel:
            self.viewPort.bind('<Enter>', self.onEnter)                                 # bind wheel events when the cursor enters the control
            self.viewPort.bind('<Leave>', self.onLeave)                                 # unbind wheel events when the cursorl leaves the control

        self.onFrameConfigure(None)                                                 #perform an initial stretch on render, otherwise the scroll region has a tiny border until the first resize

    def onFrameConfigure(self, event):                                              
        '''Reset the scroll region to encompass the inner frame'''
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))                 #whenever the size of the frame changes, alter the scroll region respectively.

    def onCanvasConfigure(self, event):
        '''Reset the canvas window to encompass inner frame when required'''
        canvas_width = event.width
        canvas_height = event.height
        kw = {'width': canvas_width} if self.orient == 'vertical' else {'height': canvas_height}
        self.canvas.itemconfig(self.canvas_window, **kw)            #whenever the size of the canvas changes alter the window region respectively.

    def onMouseWheel(self, event):                                                  # cross platform scroll wheel event
        def func(self, *args): 
            if self.orient == 'vertical' and \
                    self.canvas.winfo_height() < self.viewPort.winfo_height():
                self.canvas.yview_scroll(*args)
            elif self.orient == 'horizontal' and \
                    self.canvas.winfo_width() < self.viewPort.winfo_width():
                self.canvas.xview_scroll(*args)
        fac = -1

        if platform.system() == 'Windows':
            func(self, int(fac*(event.delta/120)), "units")
        elif platform.system() == 'Darwin':
            func(self, int(-1 * event.delta), "units")
        else:
            if event.num == 4:
                func(self,  -1, "units" )
            elif event.num == 5:
                func(self, 1, "units" )

    def onEnter(self, event):                                                       # bind wheel events when the cursor enters the control
        if platform.system() == 'Linux':
            self.canvas.bind_all("<Button-4>", self.onMouseWheel)
            self.canvas.bind_all("<Button-5>", self.onMouseWheel)
        else:
            self.canvas.bind_all("<MouseWheel>", self.onMouseWheel)

    def onLeave(self, event):                                                       # unbind wheel events when the cursorl leaves the control
        if platform.system() == 'Linux':
            self.canvas.unbind_all("<Button-4>")
            self.canvas.unbind_all("<Button-5>")
        else:
            self.canvas.unbind_all("<MouseWheel>")

    def gotoTop(self, *args):
        self.canvas.yview_moveto(0)

def monthyear2datetime(monthyear_str):
    '''converts strings like '01/24' to a pandas datetime object (01.01.2024)
    handles mm/yy or mm/yyyy'''
    _, year = monthyear_str.split('/')
    if len(year) == 2: year_format = 'y'
    elif len(year) == 4: year_format = 'Y'
    else: raise ValueError(f'monthyear falsch formatiert. Erwartet mm/yy oder mm/yyyy, nicht {monthyear_str}')
    return pd.to_datetime(monthyear_str, format=f'%m/%{year_format}')


def delete_children(widget, leave_out=None):
    '''delete a widgets children. leave out can by a type of widget or specific
    widget'''
    for w in widget.winfo_children():
        if leave_out:
            try:
                if isinstance(w, leave_out): continue
            except TypeError: pass
            if w == leave_out: continue
        w.destroy()


root = TimelineEditor()
root.mainloop()



            