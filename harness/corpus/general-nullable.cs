//@tag: general
using System;
using System.Collections.Generic;
using MessagePack;

namespace Corpus;

public enum Mode { A, B }

[MessagePackObject]
public class Optional
{
    [Key(0)] public int? MaybeInt { get; set; }
    [Key(1)] public Mode? MaybeMode { get; set; }
    [Key(2)] public DateTime? MaybeDate { get; set; }
    [Key(3)] public string? MaybeText { get; set; }
}
