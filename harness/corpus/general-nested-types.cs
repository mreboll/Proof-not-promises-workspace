//@tag: general
using System;
using System.Collections.Generic;
using MessagePack;

namespace Corpus;

[MessagePackObject]
public class Outer
{
    [Key(0)] public Inner? Child { get; set; }

    [MessagePackObject]
    public class Inner
    {
        [Key(0)] public int Depth { get; set; }
        [Key(1)] public Inner? Next { get; set; }
    }
}
