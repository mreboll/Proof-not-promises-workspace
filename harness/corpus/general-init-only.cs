//@tag: general
using System;
using System.Collections.Generic;
using MessagePack;

namespace Corpus;

[MessagePackObject]
public class Immutable
{
    [Key(0)] public int A { get; init; }
    [Key(1)] public string B { get; init; } = "";
}
