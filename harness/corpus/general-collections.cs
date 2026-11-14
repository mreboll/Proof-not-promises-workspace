//@tag: general
using System;
using System.Collections.Generic;
using MessagePack;

namespace Corpus;

[MessagePackObject]
public class Bag
{
    [Key(0)] public int[]? Numbers { get; set; }
    [Key(1)] public List<string>? Words { get; set; }
    [Key(2)] public Dictionary<string, int>? Counts { get; set; }
    [Key(3)] public HashSet<Guid>? Ids { get; set; }
    [Key(4)] public int[][]? Jagged { get; set; }
}
