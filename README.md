# html_diff

A python script that produces a diff of two files or directories as a single, self-contained HTML file. The resulting
diff works without Javascript and will automatically switch between inline and side-by-side formats depending on
available screen space.

### Installation
```
pip install -r requirements.txt
```

### Usage
```
usage: html_diff.py [-h] [-b] [-s SYNTAX_CSS] [-t PAGETITLE] [-o OUTPUT] [--header] [--content] old new

Given two source files or directories this applicationcreates an html page which highlights the differences between the two.

positional arguments:
  old                   source file or directory to compare ("before" file)
  new                   source file or directory to compare ("after" file)

options:
  -h, --help            show this help message and exit
  -b, --open            Open output file in a browser
  -s SYNTAX_CSS, --syntax-css SYNTAX_CSS
                        Path to custom Pygments CSS file for code syntax highlighting
  -t PAGETITLE, --pagetitle PAGETITLE
                        Override page title of output HTML file
  -o OUTPUT, --output OUTPUT
                        Name of output file (default: stdout)
  --header              Only output HTML header with stylesheets and stuff, and no diff
  --content             Only output HTML content, without header
```
### Example Output

![ScreenShot](/screenshots/latest.png)
