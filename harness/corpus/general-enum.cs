//@tag: general
using System;
using System.Collections.Generic;
using MessagePack;

namespace Corpus;

public enum Color { Red, Green, Blue }

[Flags]
public enum Access : byte { None = 0, Read = 1, Write = 2 }

[MessagePackObject]
public class Pixel
{
    [Key(0)] public Color Color { get; set; }
    [Key(1)] public Access Access { get; set; }
}
