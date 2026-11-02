using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace HeartOfTheRain.App.OnlineSocial
{
    // Bounded JSON with duplicate-key/type checks before JsonUtility maps DTOs.
    // User strings never become regex patterns, code or trusted rich-text markup.
    internal static class SocialJson82
    {
        sealed class Reader {
            readonly string text; int at, nodes;
            public Reader(string text) { if(text == null || text.Length > 65536) throw new FormatException(); this.text = text; }
            void Space() { while(at < text.Length && " \r\n\t".IndexOf(text[at]) >= 0) at++; }
            bool Take(char value) { Space(); if(at >= text.Length || text[at] != value) return false; at++; return true; }
            void Need(char value) { if(!Take(value)) throw new FormatException(); }
            string String() {
                Need('"'); var value = new StringBuilder(); bool closed = false;
                while(at < text.Length) {
                    char c = text[at++]; if(c == '"') { closed = true; break; }
                    if(c < 32) throw new FormatException();
                    if(c == '\\') {
                        if(at == text.Length) throw new FormatException(); c = text[at++];
                        if(c == 'u') { if(at + 4 > text.Length) throw new FormatException(); for(int n = 0; n < 4; n++) if(!Uri.IsHexDigit(text[at + n])) throw new FormatException(); c = (char)int.Parse(text.Substring(at, 4), NumberStyles.HexNumber, CultureInfo.InvariantCulture); at += 4; }
                        else { int found = "\"\\/bfnrt".IndexOf(c); if(found < 0) throw new FormatException(); c = "\"\\/\b\f\n\r\t"[found]; }
                    }
                    value.Append(c); if(value.Length > 4096) throw new FormatException();
                }
                if(!closed) throw new FormatException();
                for(int n = 0; n < value.Length; n++) if(char.IsSurrogate(value[n])) {
                    if(!char.IsHighSurrogate(value[n]) || n + 1 >= value.Length || !char.IsLowSurrogate(value[++n])) throw new FormatException();
                }
                return value.ToString();
            }
            object Value(int depth) {
                if(depth > 12 || ++nodes > 8192) throw new FormatException(); Space(); if(at >= text.Length) throw new FormatException();
                if(text[at] == '"') return String();
                if(Take('{')) {
                    var result = new Dictionary<string, object>(StringComparer.Ordinal); if(Take('}')) return result;
                    do { string key = String(); Need(':'); if(result.ContainsKey(key)) throw new FormatException(); result.Add(key, Value(depth + 1)); } while(Take(','));
                    Need('}'); return result;
                }
                if(Take('[')) {
                    var result = new List<object>(); if(Take(']')) return result;
                    do { result.Add(Value(depth + 1)); if(result.Count > 1024) throw new FormatException(); } while(Take(',')); Need(']'); return result;
                }
                int start = at; while(at < text.Length && ",]} \r\n\t".IndexOf(text[at]) < 0) at++;
                string token = text.Substring(start, at - start);
                if(token == "true") return true; if(token == "false") return false; if(token == "null") return null;
                long number;
                if(token.Length == 0 || token == "-0" || token[0] == '+' || token.Length > 1 && token[0] == '0' || token.StartsWith("-0", StringComparison.Ordinal) ||
                   !long.TryParse(token, NumberStyles.AllowLeadingSign, CultureInfo.InvariantCulture, out number)) throw new FormatException();
                return number;
            }
            public Dictionary<string, object> Read() { var value = Object(Value(0)); Space(); if(at != text.Length) throw new FormatException(); return value; }
        }
        public static Dictionary<string, object> Read(string json) => new Reader(json).Read();
        public static Dictionary<string, object> Object(object value) { var result = value as Dictionary<string, object>; if(result == null) throw new FormatException(); return result; }
        public static object Field(Dictionary<string, object> value, string key) { object field; if(!value.TryGetValue(key, out field)) throw new FormatException(); return field; }
        public static string Text(Dictionary<string, object> value, string key, int maximum = 4096, bool empty = false) {
            var result = Field(value, key) as string; if(result == null || !empty && result.Length == 0 || result.Length > maximum) throw new FormatException(); return result;
        }
        public static bool Flag(Dictionary<string, object> value, string key) { object result = Field(value, key); if(!(result is bool)) throw new FormatException(); return (bool)result; }
        public static long Number(Dictionary<string, object> value, string key, long minimum = 0, long maximum = long.MaxValue) {
            object result = Field(value, key); if(!(result is long) || (long)result < minimum || (long)result > maximum) throw new FormatException(); return (long)result;
        }
        public static List<object> Array(Dictionary<string, object> value, string key, int maximum = 100) {
            var result = Field(value, key) as List<object>; if(result == null || result.Count > maximum) throw new FormatException(); return result;
        }
        // Preserve the checked tree's actual field presence/types when passing a
        // nested receipt through the same operation validator as a direct reply.
        public static string Write(object value) { var output = new StringBuilder(); Write(value, output, 0); if(output.Length > 65536) throw new FormatException(); return output.ToString(); }
        static void Quote(string value, StringBuilder output) {
            output.Append('"'); foreach(char c in value) {
                if(c == '"' || c == '\\') { output.Append('\\'); output.Append(c); }
                else if(c < 32) { output.Append("\\u"); output.Append(((int)c).ToString("x4", CultureInfo.InvariantCulture)); }
                else output.Append(c);
            } output.Append('"');
        }
        static void Write(object value, StringBuilder output, int depth) {
            if(depth > 12 || output.Length > 65536) throw new FormatException();
            if(value == null) { output.Append("null"); return; }
            if(value is string text) { Quote(text, output); return; }
            if(value is bool flag) { output.Append(flag ? "true" : "false"); return; }
            if(value is long number) { output.Append(number.ToString(CultureInfo.InvariantCulture)); return; }
            if(value is Dictionary<string, object> fields) {
                output.Append('{'); bool comma = false; foreach(var field in fields) { if(comma) output.Append(','); comma = true; Quote(field.Key, output); output.Append(':'); Write(field.Value, output, depth + 1); } output.Append('}'); return;
            }
            if(value is List<object> items) { output.Append('['); for(int n = 0; n < items.Count; n++) { if(n != 0) output.Append(','); Write(items[n], output, depth + 1); } output.Append(']'); return; }
            throw new FormatException();
        }
    }
}
