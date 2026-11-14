//@tag: general
using System;
using System.Collections.Generic;
using MessagePack;

namespace Corpus;

[MessagePackObject]
public struct Point
{
    [Key(0)] public int X;
    [Key(1)] public int Y;
}

[MessagePackObject]
public class Segment
{
    [Key(0)] public Point From { get; set; }
    [Key(1)] public Point To { get; set; }
}
