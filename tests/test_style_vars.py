"""Test the style-vars extension logic with your own prompt and styles.

Usage:
    python test_style_vars.py                    # runs built-in test cases
    python test_style_vars.py "my $prompt here"  # test a specific prompt
"""

import re
import random
import sys

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
    depth = 0
    start = -1
    end = -1
    mode = "random"
    splits = []
    rand = random.Random(seed + (1 if neg else 0))
    if len(text) == 0:
        return text
    i = -1
    while i + 1 < len(text):
        i += 1
        if is_opening(text, i):
            if depth == 0 and text[i] != '{':
                continue
            if depth == 0:
                start = i
            depth += 1
        elif is_closing(text, i):
            if depth > 0:
                depth -= 1
            if depth == 0 and text[i] == '}' and start != -1:
                end = i
        elif text[i] == '|' and depth == 1:
            splits.append(i)
        elif text[i] == ':' and depth == 1:
            splits.append(i)
            mode = "hr"
        if end != -1:
            if mode == "hr" and len(splits) > 1:
                return text
            if mode == "hr":
                part1 = text[start+1:splits[0]]
                part2 = text[splits[0]+1:end]
                part = part2 if hires else part1
                text = text[:start] + part + text[end+1:]
            elif mode == "random":
                parts = []
                if len(splits) == 0:
                    parts.append(text[start+1:end])
                else:
                    for k in range(len(splits)):
                        if k == 0:
                            parts.append(text[start+1:splits[k]])
                        else:
                            parts.append(text[splits[k-1]+1:splits[k]])
                    parts.append(text[splits[-1]+1:end])
                custom_seed = parts.pop(0) if re_group.match(parts[0]) else None
                if custom_seed:
                    part = random.Random(str(seed) + custom_seed).choice(parts)
                else:
                    part = rand.choice(parts)
                text = text[:start] + part + text[end+1:]
            else:
                start += 1
            i = start - 1
            start = -1
            end = -1
            splits = []
            mode = "random"
    return text

def clean_linebreaks(text):
    text = re.sub(r"[\s,]*[\n\r]+[\s,]*", ", ", text)
    text = re.sub(r"\s+", " ", text).strip(", ")
    return text

def rewrite_prompt(prompt, styles, neg=False, hires=False, seed=42, clean_lb=True):
    style_names = sorted(styles.keys(), key=len, reverse=True)
    depth = 0
    previous_prompt = prompt
    while depth < 5:
        prompt = decode(prompt, hires, neg, seed)
        for name in style_names:
            if name not in prompt:
                continue
            mode = 2 if neg else 1
            text = styles[name][mode]
            parts = [p.strip() for p in re_prompt.split(text)]
            text = ", ".join(parts)
            if clean_lb:
                text = clean_linebreaks(text)
            if " " not in name:
                prompt = prompt.replace(f"{var_char}{name}", text)
            prompt = prompt.replace(f"{var_char}({name})", text)
            for i, part in enumerate(parts):
                if " " not in name:
                    prompt = prompt.replace(f"{var_char}{i+1}{name}", part)
                prompt = prompt.replace(f"{var_char}{i+1}({name})", part)
        if prompt == previous_prompt:
            break
        previous_prompt = prompt
        depth += 1
    return prompt


# Mock styles: {name: (name, positive, negative)}
mock_styles = {
    "cinematic": ("cinematic", "cinematic perspective, letterboxing", "colorful, cute, vibrant"),
    "detailed": ("detailed",
        "masterpiece, best quality,\nextremely detailed face,\nintricate eyes",
        "low quality, worst quality"),
    "multiline": ("multiline", "line one\nline two\nline three", "bad, ugly"),
    "artistic": ("artistic",
        "van gogh\n{prompt}\nabstract artstyle\n{prompt}\nlandscape",
        "blurry, ugly"),
}

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--":
            prompt = sys.stdin.read()
        else:
            prompt = " ".join(sys.argv[1:])
        result = rewrite_prompt(prompt, mock_styles)
        print(f"Input:  {repr(prompt)}")
        print(f"Output: {repr(result)}")
    else:
        print("=== Style-Vars Tests ===\n")
        tests = [
            ("single-line style", "oil painting, $cinematic, man"),
            ("multi-line style (no {prompt})", "portrait, $multiline, sunset"),
            ("multi-line with {prompt}", "fantasy, $artistic, dragon"),
            ("newlines in parts", "detailed, $detailed, portrait"),
            ("line breaks in prompt", "oil painting\n$cinematic\nportrait"),
            ("$1 part syntax", "landscape, $1artistic, man"),
        ]
        for desc, prompt in tests:
            result = rewrite_prompt(prompt, mock_styles)
            print(f"[{desc}]")
            print(f"  In:  {repr(prompt)}")
            print(f"  Out: {repr(result)}")
            print()

        print("--- Negative mode tests ---")
        neg_tests = [
            ("negative with $cinematic", "3D, $cinematic"),
            ("negative with $multiline", "bad, $multiline"),
        ]
        for desc, prompt in neg_tests:
            result = rewrite_prompt(prompt, mock_styles, neg=True)
            print(f"[{desc}]")
            print(f"  In:  {repr(prompt)}")
            print(f"  Out: {repr(result)}")
            print()

        print("Usage: python test_style_vars.py \"your \\$prompt here\"")
