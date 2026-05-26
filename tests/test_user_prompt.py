"""Test the style-vars extension with the user's exact prompt."""
import sys, re, random

var_char = "$"
re_prompt = re.compile(r",? *\{prompt\} *,? *", re.I)
re_group = re.compile(r"^_\d+_$")

def is_opening(text, i):
    chars = ['{', '(', '[', '<']
    return text[i] in chars and (i == 0 or text[i-1] != '\\')
def is_closing(text, i):
    chars = ['}', ')', ']', '>']
    return text[i] in chars and (i == 0 or text[i-1] != '\\')

def decode(text, hires, neg, seed):
    depth = 0; start = -1; end = -1; mode = "random"; splits = []
    rand = random.Random(seed + (1 if neg else 0))
    if len(text) == 0: return text
    i = -1
    while i + 1 < len(text):
        i += 1
        if is_opening(text, i):
            if depth == 0 and text[i] != '{': continue
            if depth == 0: start = i
            depth += 1
        elif is_closing(text, i):
            if depth > 0: depth -= 1
            if depth == 0 and text[i] == '}' and start != -1: end = i
        elif text[i] == '|' and depth == 1: splits.append(i)
        elif text[i] == ':' and depth == 1: splits.append(i); mode = "hr"
        if end != -1:
            if mode == "hr" and len(splits) > 1: return text
            if mode == "hr":
                part = text[splits[0]+1:end] if hires else text[start+1:splits[0]]
                text = text[:start] + part + text[end+1:]
            elif mode == "random":
                parts = []
                if len(splits) == 0: parts.append(text[start+1:end])
                else:
                    for k in range(len(splits)):
                        parts.append(text[(start+1 if k==0 else splits[k-1]+1):splits[k]])
                    parts.append(text[splits[-1]+1:end])
                custom_seed = parts.pop(0) if re_group.match(parts[0]) else None
                part = random.Random(str(seed) + custom_seed).choice(parts) if custom_seed else rand.choice(parts)
                text = text[:start] + part + text[end+1:]
            else: start += 1
            i = start - 1; start = -1; end = -1; splits = []; mode = "random"
    return text

def clean_linebreaks(text):
    text = re.sub(r"[\s,]*[\n\r]+[\s,]*", ", ", text)
    text = re.sub(r"\s+", " ", text).strip(", ")
    return text

# User's exact prompt with real newlines
prompt = """, @noct, masterpiece, 
<lora:NoctAnimaV7:0.2@0; 0.6@9; 0.75@15:hr=0.75>

1girl, adult woman, mature female,
orange hair, long hair, freckles, green eyes, blush, looking at viewer, wide smile, """

print("=== INPUT ===")
print(repr(prompt))
print()

# Test just line break cleaning
print("=== AFTER LINEBREAK CLEANING ===")
result = clean_linebreaks(prompt)
print(repr(result))
print()
print(result)
print()

# Test full rewrite with no styles (no $vars in prompt)
print("=== FULL REWRITE (no styles) ===")
result = clean_linebreaks(prompt)
depth = 0
while depth < 5:
    result = decode(result, False, False, 42)
    if depth > 0 and result == previous: break
    previous = result
    depth += 1
print(repr(result))
