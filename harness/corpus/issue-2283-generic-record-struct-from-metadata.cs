//@tag: issue-2283
//@library
using MessagePack;

namespace Lib;

[MessagePackObject]
public partial record struct Item<T>([property: Key(0)] string Key);
//@main
using MessagePack;
using Lib;

namespace App;

[MessagePackObject]
public sealed partial record Cmd([property: Key(0)] string Scope)
{
    [Key(1)]
    public Item<int> Member { get; init; }
}

[GeneratedMessagePackResolver]
partial class AppResolver { }
