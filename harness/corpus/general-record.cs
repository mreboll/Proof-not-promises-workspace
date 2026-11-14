//@tag: general
using System;
using System.Collections.Generic;
using MessagePack;

namespace Corpus;

[MessagePackObject]
public record Money([property: Key(0)] decimal Amount, [property: Key(1)] string Currency);
