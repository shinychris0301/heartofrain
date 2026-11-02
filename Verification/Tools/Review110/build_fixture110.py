"""Assemble the independently owned native110 fixture from reviewed109 capture primitives.

This is source preparation only: it does not invoke Unity or network code.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
OLD = ROOT / 'Unity/Assets/HeartOfTheRain/Verification/Editor/TeamsAccess109Verification.cs'
FOUNDATION = Path(__file__).with_name('TeamsChatHelp110Verification.cs.template')
PARTS = Path(__file__).with_name('TeamsChatHelp110Verification.parts.cs.txt')
OUT = Path(__file__).with_name('TeamsChatHelp110Verification.final.cs.txt')

def method(text, signature):
    start = text.index(signature)
    brace = text.index('{', start)
    # Capture methods have no braces in literals that are unbalanced.
    level = 1
    for p in range(brace + 1, len(text)):
        if text[p] == '{': level += 1
        elif text[p] == '}':
            level -= 1
            if level == 0: return text[start:p+1]
    raise ValueError(signature)

def main():
    text = FOUNDATION.read_text(encoding='utf-8')
    text = text.replace('using HeartOfTheRain.App.Teams;','using HeartOfTheRain.App.Teams;\nusing HeartOfTheRain.App.TeamsSocial;')
    text = text.replace('   public int checks,cases,layoutsAttempted,layouts,scriptedExchanges,actualHttpRequests,animationCases;',
                        '   public int checks,cases,layoutsAttempted,layouts,scriptedExchanges,actualHttpRequests,animationCases,capturedSentinelPixels;\n   public bool rawJsonNullOwnRequestMaterializes;')
    text = re.sub(r' // Staged verifier foundation only\.[\s\S]*? public static class',
                  ' // Independent actual-client/scripted transport and separately labelled visual fixture.\n public static class', text, count=1)
    old = OLD.read_text(encoding='utf-8')
    capture = method(old, '        static void Capture(').replace('Teams109','Teams110').replace('Native/TeamsAccess109/','Native/TeamsChatHelp110/')
    prepare = method(old, '        static void PrepareCanvas(')
    suffix = '\n'+prepare+'\n'+capture+'\n'+PARTS.read_text(encoding='utf-8')+'\n }\n}\n#endif\n'
    text = text[:text.rfind('\n }\n}\n#endif')]+suffix
    OUT.write_text(text,encoding='utf-8',newline='\n')
    print(OUT.relative_to(ROOT))

if __name__ == '__main__': main()
