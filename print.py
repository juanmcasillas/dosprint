#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# /////////////////////////////////////////////////////////////////////////////
# //
# // print.py 
# //
# // Encapsulate the program, to do some pretty printing for Retro
# // EPSON and other things
# // https://github.com/juanmcasillas/dosprint
# //
# // 11/08/2025 09:51:27  
# // (c) 2025 Juan M. Casillas <juanm.casillas@gmail.com>
# // 
# // Print from DOSBox (or raw input) using EPSON FX dialect (or postcript)
# //
# /////////////////////////////////////////////////////////////////////////////

# see https://github.com/RWAP/PrinterToPDF
# changed the code to write png to disk (initialize function, PrinterConvert.c:463 imageMode = 2):
# use: ./print.py -v -m pm ../pmmain_000.prt # EPSON
# use: ./print.py -v -g ../wp_001.prt # postcript output
# apt-get install python3-pypdf2
# apt-get install python3-pil
# apt-get install ghostcript

# A0: 841 x 1189 mm (33.1 x 46.8 inches)
# A1: 594 x  841 mm (23.4 x 33.1 inches)
# A2: 420 x  594 mm (16.5 x 23.4 inches)
# A3: 297 x  420 mm (11.7 x 16.5 inches)
# A4: 210 x  297 mm (8.3 x 11.7 inches)
# A5: 148 x  210 mm (5.8 x 8.3 inches)
# A6: 105 x  148 mm (4.1 x 5.8 inches)
# A7:  74 x  105 mm (2.9 x 4.1 inches)
# A8:  52 x   74 mm (2.0 x 2.9 inches)
# A9:  37 x   52 mm (1.5 x 2.0 inches)
# A10: 26 x   37 mm (1.0 x 1.5 inches) 

import argparse
import sys
import subprocess
import os
import shutil
import PyPDF2
import pathlib
import tempfile 
import re
import glob
from PIL import Image

class PrintManager:
    cmd = "./printerToPDF_png"
    gs  = "/usr/bin/gs" 
    font = "font2/Epson-Standard.C16"
    sizes = {
        'A4'     : [210,297    , 2.5, 2.5, 2.5, 2.5],   # page_width, page_height, ML, MR, MT, MB (Margins) A4
        'folio'  : [215,315    , 2.5, 2.5, 2.5, 2.5],   # page_width, page_height, ML, MR, MT, MB (Margins) Old paper size (mine)
        'fp'     : [210,310    , 0,   0,   0,   0  ],   # page_width, page_height, ML, MR, MT, MB (Margins) Custom Firt Publisher Size (A4+)
        'Letter' : [215.9,279.4, 2.5, 2.5, 2.5, 2.5],   # page_width, page_height, ML, MR, MT, MB (Margins) Letter
        'pmmain' : [205,335    , 2.5, 2.5, 2.5, 2.5],   # page_width, page_height, ML, MR, MT, MB (Margins) Print Master (very large page)
    }
    sizes['generic'] = sizes['A4'] 
    #sizes['fp'] = sizes['A4']       # First Publisher uses a A4 page size (custom size)

    generic_mode = 'generic'
    auto_mode = 'auto'

    sizes_keys_lower = list(map(lambda x: x.lower(), sizes.keys()))
    sizes_keys_lower.append(auto_mode)
    print_ext = "prt"
    print_re = r"([A-z]+)_\d+\.%s" % print_ext

    def __init__(self, args):
        self.verbose = args.verbose
        self.landscape = args.landscape
        self.preserve = args.preserve
        self.mode = args.mode 
        self.gs = args.gs
        self.dirmode = False
        if not self.mode:
            self.mode = PrintManager.auto_mode

        if not self.mode.lower() in PrintManager.sizes_keys_lower:
            raise ValueError("mode must be a valid key: %s" % list(PrintManager.sizes.keys()))

     
    def _set_sizes_by_mode(self, mode):
        self.page_width, self.page_height, self.ML, self.MR, self.MT, self.MB = PrintManager.sizes[mode]
        if self.landscape:
            w = self.page_width
            self.page_width = self.page_height
            self.page_height = w

    def _print(self, *args):
        if self.verbose:
            print(*args)

    def run_one_file(self, input_file):

        self._print("[BEGIN] [%s] ---" % input_file)

        temp_dir_obj = tempfile.TemporaryDirectory(prefix="print", delete= not self.preserve)
        temp_dir = temp_dir_obj.name

        if not self.gs:
            # EPSON mode
            # try to guess mode if mode == "auto"
            file_mode = self.mode
            if file_mode == PrintManager.auto_mode:
                fn = os.path.basename(input_file)
                r = re.search(PrintManager.print_re, fn, re.I)
                if r is not None:
                    file_mode = r.group(1)
                    if not file_mode.lower() in PrintManager.sizes_keys_lower:
                        # use generic or stablished.
                        file_mode = PrintManager.generic_mode
                    

            self._print(" -> mode selected by file: %s" % file_mode)
            self._set_sizes_by_mode(file_mode)   

            s = f"{PrintManager.cmd} -o {temp_dir} -f {PrintManager.font} -p {self.page_width},{self.page_height} -m {self.ML},{self.MR},{self.MT},{self.MB} {input_file}"

        else:
            ## postcript output (PS)
            output_ps_dir = "%s/pdf" %  temp_dir
            output_png_dir = "%s/png" %  temp_dir
            os.makedirs(output_ps_dir)
            os.makedirs(output_png_dir)
            s = f"{PrintManager.gs} -sDEVICE=pdfwrite -dPDFSETTINGS=/prepress -dHaveTrueTypes=true -dEmbedAllFonts=true  -dSubsetFonts=false -o '{output_ps_dir}/page%d.pdf' -DNOSAFER  -dNOPAUSE -dBATCH -f {input_file}"


        self._print(" -> Command [%s]" % s)
        output_stdout = subprocess.Popen(s, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE).stdout
        if self.verbose:
            for i in output_stdout.readlines():
                self._print("  > ", i.decode("utf-8").strip())
            

        if self.gs:
            # create png images 
            self._print(" -> GS PNG Command [%s]" % s)
            s = f"{PrintManager.gs} -q -sPAPERSIZE=a4 -sDEVICE=png16m -dTextAlphaBits=4 -r720x720 -o '{output_png_dir}/page%d.png' -DNOSAFER -dNOPAUSE -dBATCH  -f {input_file}"
            output_stdout = subprocess.Popen(s, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE).stdout
            if self.verbose:
                for i in output_stdout.readlines():
                    self._print("  > ", i.decode("utf-8").strip())


        self.merge(input_file, temp_dir)
        self._print("[END] ---")
        
        #temp file is cleaned automatically
        #self.clean(output_dir)


    def run(self, file_list):
        
        # input_file is an array.
        for fn in file_list:
            if not os.path.exists(fn):
                raise ValueError("input file (or dir) %s doesn't exists" % fn)

            self.run_one_file(fn)
        
        self._print("\nDone! (%d files processed)" % len(file_list))


        
    def clean(self, output_dir):
        # clean the thing a little. if multi page pdf, create a one file with all the pages.
        self._print(" -> Cleaning %s/{eps,png,pdf} dirs" % output_dir)
        shutil.rmtree("%s/eps" % output_dir) 
        shutil.rmtree("%s/png" % output_dir)
        shutil.rmtree("%s/pdf" % output_dir)
        
        # clean the pdf.


    def is_blank_page(self, page) -> bool:
        has_text = bool(page.extract_text().strip())
        has_image = False
        x_object = page["/Resources"]["/XObject"].getObject()
        for obj in x_object:
            if x_object[obj]["/Subtype"] == "/Image":
                has_image = True
        if has_text or has_image:
            return False
        return True

    def check_full_histogram(self, fp):
        # use the file stored as png as "print" image to check if the histogram has any 
        # black pixel. Retrun True if some data (image) is found.
        img = Image.open(fp).convert("1")
        histogram = img.histogram()
        if histogram[0] == 0:
            return False
        return True # not empty


    def merge(self, input_file, output_dir):
        target_file = "%s/%s.pdf" % (output_dir, pathlib.Path(input_file).stem)
        final_file = "%s/%s.pdf" % (os.path.dirname(input_file), pathlib.Path(input_file).stem)
        pdf_dir = "%s/pdf" % output_dir
        png_dir = "%s/png" % output_dir

        x = [a for a in sorted(os.listdir(pdf_dir)) if a.endswith(".pdf")]
        merger = PyPDF2.PdfMerger()

        self._print(" -> Merging %d pdf pages into %s" % (len(x), target_file))

        for pdf in x:
            pdf_file = "%s/%s" % (pdf_dir,pdf)
            png_file = "%s/%s.png" % (png_dir,pathlib.Path(pdf).stem)
            # check if the png file has something.
            if self.check_full_histogram(png_file):
                merger.append(open(pdf_file, 'rb'))
            else:
                self._print(" -> Empty page found at %s" % pdf_file)

        with open(target_file, "wb") as fout:
            merger.write(fout)

        # store the file at the same level
        shutil.copy(target_file, final_file)
        self._print(" -> Copy %s -> %s" % (target_file, final_file))

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", help="show data about file and processing", action="count", default=0)
    parser.add_argument("-l", "--landscape", help="select Landscape mode", action="store_true", default=False)
    parser.add_argument("-p", "--preserve", help="preserve data", action="store_true", default=False)
    parser.add_argument("-g", "--gs", help="run using Ghostcript to generate PDF (PS printing)", action="store_true", default=False)
    parser.add_argument("-m", "--mode", help="select mode", 
                        choices= list(PrintManager.sizes.keys()).append(PrintManager.auto_mode), 
                        default=PrintManager.auto_mode)
                        
    parser.add_argument("input", help="input file to print (support dir on batchmode)", nargs="+")
    args = parser.parse_args()

    pm = PrintManager(args)
    pm.run(args.input)
    
