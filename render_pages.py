import fitz

def render():
    # Render page 1 of original
    doc_orig = fitz.open("INV_IG_ETD 21.05.PDF")
    pix_orig = doc_orig[0].get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
    pix_orig.save("orig_page.png")
    doc_orig.close()
    print("Saved orig_page.png")
    
    # Render page 1 of cleaned
    doc_clean = fitz.open("cleaned_test.pdf")
    pix_clean = doc_clean[0].get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
    pix_clean.save("cleaned_page.png")
    doc_clean.close()
    print("Saved cleaned_page.png")

if __name__ == "__main__":
    render()
