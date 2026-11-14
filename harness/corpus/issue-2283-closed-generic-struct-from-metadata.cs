//@tag: issue-2283
//@library
using MessagePack;

namespace Lib
{
    [MessagePackObject]
    public struct Box<T>
    {
        [Key(0)] public T Content { get; set; }
    }
}
//@main
using MessagePack;
using Lib;

namespace App
{
    [MessagePackObject]
    public class Holder
    {
        [Key(0)] public Box<int> Value { get; set; }
    }

    [GeneratedMessagePackResolver]
    partial class AppResolver { }
}
