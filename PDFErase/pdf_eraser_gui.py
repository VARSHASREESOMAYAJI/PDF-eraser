import fitz  # PyMuPDF
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import io

class PDFEraser:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Eraser - Scrollable Version")
        self.root.geometry("1000x750")

        # PDF state
        self.doc = None
        self.page_index = 0
        self.tk_img = None
        self.start_x = self.start_y = None
        self.rect = None
        self.erasures = {}
        self.image_id = None

        # Frame with scrollbars
        frame = tk.Frame(root)
        frame.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(frame, bg="gray")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.v_scroll = tk.Scrollbar(frame, orient="vertical", command=self.canvas.yview)
        self.v_scroll.pack(side="right", fill="y")

        self.h_scroll = tk.Scrollbar(root, orient="horizontal", command=self.canvas.xview)
        self.h_scroll.pack(side="bottom", fill="x")

        self.canvas.config(yscrollcommand=self.v_scroll.set, xscrollcommand=self.h_scroll.set)

        # Toolbar
        toolbar = tk.Frame(root)
        toolbar.pack(fill="x")

        tk.Button(toolbar, text="Open PDF", command=self.open_pdf).pack(side="left", padx=5)
        tk.Button(toolbar, text="Prev Page", command=self.prev_page).pack(side="left", padx=5)
        tk.Button(toolbar, text="Next Page", command=self.next_page).pack(side="left", padx=5)
        tk.Button(toolbar, text="Save Edited PDF", command=self.save_pdf).pack(side="right", padx=5)

        self.page_label = tk.Label(toolbar, text="Page: 0/0")
        self.page_label.pack(side="right", padx=10)

        # Bindings
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind_all("<MouseWheel>", self.on_scroll)

    def open_pdf(self):
        file = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if not file:
            return
        self.doc = fitz.open(file)
        self.page_index = 0
        self.erasures.clear()
        self.file_path = file
        self.show_page()

    def render_page(self):
        page = self.doc.load_page(self.page_index)
        zoom = 1.5
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        img = Image.open(io.BytesIO(pix.tobytes("ppm")))
        return img

    def show_page(self):
        if not self.doc:
            return
        img = self.render_page()
        self.tk_img = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        self.image_id = self.canvas.create_image(0, 0, image=self.tk_img, anchor="nw")
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        self.page_label.config(text=f"Page: {self.page_index+1}/{len(self.doc)}")

    def on_scroll(self, event):
        # Windows uses event.delta in multiples of 120
        self.canvas.yview_scroll(-1 * int(event.delta / 120), "units")

    def next_page(self):
        if self.doc and self.page_index < len(self.doc) - 1:
            self.page_index += 1
            self.show_page()

    def prev_page(self):
        if self.doc and self.page_index > 0:
            self.page_index -= 1
            self.show_page()

    def on_press(self, event):
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, event.x, event.y, outline="red")

    def on_drag(self, event):
        if self.rect:
            cur_x = self.canvas.canvasx(event.x)
            cur_y = self.canvas.canvasy(event.y)
            self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_release(self, event):
        if not self.doc or not self.rect:
            return
        x0, y0, x1, y1 = self.canvas.coords(self.rect)
        img = self.render_page()
        page = self.doc.load_page(self.page_index)

        # Scaling fix: PDF vs displayed image
        w_ratio = img.width / page.rect.width
        h_ratio = img.height / page.rect.height
        pdf_x0, pdf_y0 = x0 / w_ratio, y0 / h_ratio
        pdf_x1, pdf_y1 = x1 / w_ratio, y1 / h_ratio
        r = fitz.Rect(pdf_x0, pdf_y0, pdf_x1, pdf_y1)

        self.erasures.setdefault(self.page_index, []).append(r)
        self.canvas.create_rectangle(x0, y0, x1, y1, fill="white", outline="white")
        self.rect = None

    def save_pdf(self):
        if not self.doc:
            messagebox.showerror("Error", "No PDF loaded.")
            return

        for pno, rects in self.erasures.items():
            page = self.doc.load_page(pno)
            for r in rects:
                page.add_redact_annot(r, fill=(1, 1, 1))
            page.apply_redactions()

        out_file = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF Files", "*.pdf")])
        if out_file:
            self.doc.save(out_file, garbage=4, deflate=True)
            messagebox.showinfo("Saved", f"Edited PDF saved:\n{out_file}")

if __name__ == "__main__":
    root = tk.Tk()
    app = PDFEraser(root)
    root.mainloop()
