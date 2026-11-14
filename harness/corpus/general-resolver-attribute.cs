//@tag: general
using System;
using System.Collections.Generic;
using MessagePack;

namespace Corpus;

[MessagePackObject]
public class Item { [Key(0)] public int Id { get; set; } }

[GeneratedMessagePackResolver]
public partial class CorpusResolver { }
