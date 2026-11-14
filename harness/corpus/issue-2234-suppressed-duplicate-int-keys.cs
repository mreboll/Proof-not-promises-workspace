//@tag: issue-2234
using MessagePack;

namespace Corpus;

[MessagePackObject(SuppressSourceGeneration = true)]
public class DupInt
{
    [Key(0)] public string? A { get; set; }
    [Key(0)] public string? B { get; set; }
}
