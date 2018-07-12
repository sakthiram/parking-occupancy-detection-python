import boto3
import tkinter as tk
from PIL import Image, ImageTk, ImageChops
import json
import time, datetime
import numpy as np

min_pixels = 100

class TKcanvas_setup(tk.Toplevel):
    def __init__(self, setup_image, master):
#         tk.Toplevel.__init__(self)
        #tk.Tk.__init__(self)
        self.x = self.y = 0
        self.image = ImageTk.PhotoImage(setup_image, master) # Use correct master else create_image fails (when Toplevel not used)
        self.canvas = tk.Canvas(master, width=1000, height=700, cursor="cross", scrollregion=(0,0,self.image.width(), self.image.height()))
        self.canvas.pack(side="top", fill="both", expand=True)
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        self.canvas.bind("<B1-Motion>", self.on_button_move)
        self.canvas.create_image(0, 0, image=self.image, anchor=tk.NW)
        # Scroll
        self.canvas.pack(side=tk.TOP, fill="both", expand=True)
        self.scrollbar_horizontal = tk.Scrollbar(master, orient="horizontal", command=self.canvas.xview)
        self.scrollbar_horizontal.pack(side=tk.BOTTOM, fill=tk.X)
        self.scrollbar_vertical = tk.Scrollbar(master, orient="vertical", command=self.canvas.yview)
        self.scrollbar_vertical.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.config(xscrollcommand=self.scrollbar_horizontal.set, yscrollcommand=self.scrollbar_vertical.set)

        self.lines = []
        # Can combine below variables into struct & create a list of struct instead of "list of each var"
        self.obj_list = []
        self.full_obj_marker_list = []
        self.saved_rect_list = []
        self.saved_obj_text = []

    def on_button_press(self, event):
        self.x = self.canvas.canvasx(event.x)
        self.y = self.canvas.canvasy(event.y)

    def on_button_move(self, event):
        x0, y0 = (self.x, self.y)
        x1, y1 = (self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))

        # Remove lines
        for line_id in self.lines:
            self.canvas.delete(line_id)

        self.lines = []

        self.lines.append(self.canvas.create_line(x0, y0, x0, y1, fill="black"))
        self.lines.append(self.canvas.create_line(x0, y1, x1, y1, fill="black"))
        self.lines.append(self.canvas.create_line(x1, y1, x1, y0, fill="black"))
        self.lines.append(self.canvas.create_line(x1, y0, x0, y0, fill="black"))

    def on_button_release(self, event):
        x0, y0 = (self.x, self.y)
        x1, y1 = (self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))

        for line_id in self.lines:
            self.canvas.delete(line_id)

        self.lines = []

        self.lines.append(self.canvas.create_line(x0, y0, x0, y1, fill="red"))
        self.lines.append(self.canvas.create_line(x0, y1, x1, y1, fill="red"))
        self.lines.append(self.canvas.create_line(x1, y1, x1, y0, fill="red"))
        self.lines.append(self.canvas.create_line(x1, y0, x0, y0, fill="red"))
#       self.canvas.create_rectangle(x0, y0, x1, y1, fill="black")

        self.full_obj_marker = (x0, y0, x1, y1)
        if (x1-x0 < min_pixels or y1-y0 < min_pixels):
            self.show_warning_box("WARNING: Width/Height of the box is less than "+str(min_pixels)+" pixels.")
            return
        obj_name = self.get_object_info(())
    
    def show_warning_box(self, text):
        warn_box = tk.Tk()
        tk.Label(warn_box, text=text).grid(row=0)
        tk.Button(warn_box, text='OK', command=warn_box.destroy).grid(row=1)

    def get_object_info(self, full_obj_marker):
        obj_entry_box = tk.Tk()
        tk.Label(obj_entry_box, text="Item Name").grid(row=0)
        self.e1 = tk.Entry(obj_entry_box)
        self.e1.grid(row=0, column=1)
        tk.Button(obj_entry_box, text='Save', command=lambda: self.save_marker(obj_entry_box)).grid(row=2, column=0, sticky=tk.W, pady=4)
        tk.Button(obj_entry_box, text='Quit', command=obj_entry_box.destroy).grid(row=2, column=1, sticky=tk.W, pady=4)
        tk.Button(obj_entry_box, text='Delete', command=lambda: self.del_marker(obj_entry_box)).grid(row=2, column=3, sticky=tk.W, pady=4)

    def save_marker(self, box):
        obj_name = self.e1.get()
        if (obj_name not in self.obj_list and self.full_obj_marker not in self.full_obj_marker_list):
            self.obj_list.append(obj_name)
            self.full_obj_marker_list.append(self.full_obj_marker)
            self.saved_rect_list.append(self.canvas.create_rectangle(self.full_obj_marker, outline="green"))
            center_x = (self.full_obj_marker[0]+self.full_obj_marker[2])/2
            center_y = (self.full_obj_marker[1]+self.full_obj_marker[3])/2
            self.saved_obj_text.append(self.canvas.create_text(center_x, center_y, fill="green",
                                                               font="Times 20 italic bold", text=obj_name))
        else:
            # Add another dialog box that warns user that the obj_name already exists
            print ("Warning: Object name or Marker already present")
        box.destroy()
    
    def del_marker(self, box):
        obj_name = self.e1.get()
        if obj_name in self.obj_list:  
            obj_idx  = self.obj_list.index(obj_name)
            self.obj_list.pop(obj_idx)
            self.full_obj_marker_list.pop(obj_idx)
            self.canvas.delete(self.saved_rect_list[obj_idx])
            self.saved_rect_list.pop(obj_idx)
            self.canvas.delete(self.saved_obj_text[obj_idx])
            self.saved_obj_text.pop(obj_idx)
        else:
            # Add another dialog box that warns user that the obj_name already exists
            print ("Warning: Object name not present")
        box.destroy()

# Function to convert a standard Python dict to a boto3 dynamodb item
def dict_to_item(raw):
    if type(raw) is dict:
        resp = {}
        for k,v in raw.items():
            if type(v) is str:
                resp[k] = {
                    'S': v
                }
            elif type(v) is int:
                resp[k] = {
                    'I': str(v)
                }
            elif type(v) is dict:
                resp[k] = {
                    'M': dict_to_item(v)
                }
            elif type(v) is list:
                resp[k] = []
                for i in v:
                    resp[k].append(dict_to_item(i))
        return resp
    elif type(raw) is str:
        return {
            'S': raw
        }
    elif type(raw) is int:
        return {
            'I': str(raw)
        }

# SETUP BOXES
#setup_image = Image.open("test.jpg")
setup_image = Image.open("parking_7thfloor_4MP.jpg")
#root = tk.Toplevel()

root = tk.Tk()
TKcanvas_setup_inst = TKcanvas_setup(setup_image, root)
root.mainloop()

boxes = {}
for (idx,region) in enumerate(TKcanvas_setup_inst.obj_list):
    boxes[region] = list(TKcanvas_setup_inst.full_obj_marker_list[idx])

print("Boxes JSON format => ", json.dumps(boxes), "\n")
print("Boxes DynamoDB format => ", dict_to_item(boxes), "\n")

# SEND BOXES' COORDINATES TO DYNAMODB TABLE
dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
table = dynamodb.Table('CE_Status_Table')

respomse = table.put_item(
    Item = {
        'DSN': 'W3',
        'Timestamp': datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%dT%H:%M:%S'),
        'BattVol': str(3450),
        'isBattPowered': True,
        'isOnline': False,
        'Application': 'car-parking-occupancy-detection',
        'lambdaParams': dict_to_item(boxes),
        'lambdaResults': {}
    }
)