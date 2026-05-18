import sys, traceback

sys.stderr = open('D:/I-Study/desktop_err.txt', 'w', encoding='utf-8')
sys.stdout = open('D:/I-Study/desktop_out.txt', 'w', encoding='utf-8')

try:
    from main import main
    main()
except Exception as e:
    traceback.print_exc()
    sys.stderr.flush()
