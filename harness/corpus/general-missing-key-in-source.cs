//@tag: general
using System;
using System.Collections.Generic;
using MessagePack;

namespace Corpus;

[MessagePackObject]
public class Broken
{
    [Key(0)] public int Ok { get; set; }
    public int MissingKey { get; set; }
}
