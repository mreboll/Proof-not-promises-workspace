//@tag: general
using MessagePack;

namespace Corpus;

[MessagePackObject]
public class DupIntGenerated
{
    [Key(0)] public string? A { get; set; }
    [Key(0)] public string? B { get; set; }
}
