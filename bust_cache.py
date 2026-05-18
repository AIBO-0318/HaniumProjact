import os, glob

pages = glob.glob(r'D:\I-Study\ui_ux\web\pages\*.html')
for p in pages:
    with open(p, 'r', encoding='utf-8') as f:
        content = f.read()
    new = content
    for old in ['style.css"', 'style.css?v=1"', 'style.css?v=2"', 'style.css?v=3"']:
        new = new.replace(f'/static/css/{old}', '/static/css/style.css?v=4"')
    if new != content:
        with open(p, 'w', encoding='utf-8') as f:
            f.write(new)
        print('updated:', os.path.basename(p))
    else:
        print('skipped:', os.path.basename(p))
print('완료')
