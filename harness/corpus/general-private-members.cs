//@tag: general
using System;
using System.Collections.Generic;
using MessagePack;

namespace Corpus;

[MessagePackObject(AllowPrivate = true)]
public partial class Secretive
{
    [Key(0)] private int hidden;
    [Key(1)] internal string? Internal { get; set; }

    [IgnoreMember] public int Hidden => hidden;
}
