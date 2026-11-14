//@tag: general
using System;
using System.Collections.Generic;
using MessagePack;

namespace Corpus;

[MessagePackObject(keyAsPropertyName: true)]
public class Auto
{
    public string? Title { get; set; }
    public int Count { get; set; }
}
